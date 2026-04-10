// ============================================================================
// POMS — Azure infrastructure
//
// Provisions:
//   - Log Analytics workspace (Container Apps observability sink)
//   - Azure Container Registry (Basic)
//   - User-assigned managed identity with AcrPull on the registry
//   - Storage account + file share (persists the LanceDB vector store)
//   - Container Apps managed environment with the file share mounted
//   - PostgreSQL Flexible Server (Burstable B1ms) + application database
//   - Azure OpenAI account with GPT-4o-mini + text-embedding-3-large deployments
//   - Container App running the FastAPI backend + Gmail poller
//   - Static Web App (Free tier) for the React frontend
//
// Flow:
//   1. `bootstrap.sh` creates the RG and deploys this template with a
//      placeholder container image, then configures GitHub OIDC.
//   2. GitHub Actions builds the real image, pushes it to ACR, and calls
//      `az containerapp update` to roll the Container App forward.
// ============================================================================

targetScope = 'resourceGroup'

@description('Deployment region for all resources.')
param location string = resourceGroup().location

@description('Short name prefix used for every resource (lowercase, no dashes).')
@minLength(3)
@maxLength(8)
param namePrefix string = 'poms'

@description('Environment suffix — e.g. demo, dev, prod.')
param environment string = 'demo'

@description('PostgreSQL admin login.')
param postgresAdminLogin string = 'pomsadmin'

@description('PostgreSQL admin password.')
@secure()
param postgresAdminPassword string

@description('Fully qualified container image reference to deploy. Defaults to a public hello-world placeholder so the Container App can be created before CI has built the real image.')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

// ---------------------------------------------------------------------------
// Naming
// ---------------------------------------------------------------------------
var shortSuffix = substring(uniqueString(resourceGroup().id), 0, 6)

var logAnalyticsName  = 'log-${namePrefix}-${environment}'
var acrName           = toLower('cr${namePrefix}${shortSuffix}')
var identityName      = 'id-${namePrefix}-${environment}'
var storageAccountName = toLower('st${namePrefix}${shortSuffix}')
var fileShareName     = 'lancedb'
var containerEnvName  = 'cae-${namePrefix}-${environment}'
var backendAppName    = 'ca-${namePrefix}-backend'
var postgresName      = 'psql-${namePrefix}-${shortSuffix}'
var postgresDbName    = 'poms'
var openAiName        = 'oai-${namePrefix}-${shortSuffix}'
var staticWebAppName  = 'swa-${namePrefix}-${environment}'

var gptDeploymentName       = 'gpt-4o-mini'
var embeddingDeploymentName = 'text-embedding-3-large'

// ---------------------------------------------------------------------------
// Log Analytics
// ---------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ---------------------------------------------------------------------------
// Azure Container Registry — Basic tier (~$5/month)
// ---------------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

// ---------------------------------------------------------------------------
// User-assigned managed identity — used by the Container App to pull from ACR
// ---------------------------------------------------------------------------
resource containerAppIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, containerAppIdentity.id, 'AcrPull')
  scope: acr
  properties: {
    // Built-in AcrPull role
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: containerAppIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Storage account + file share — backs the LanceDB vector store
// ---------------------------------------------------------------------------
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: fileShareName
  properties: {
    shareQuota: 10
    enabledProtocols: 'SMB'
  }
}

// ---------------------------------------------------------------------------
// Container Apps environment + mounted file share
// ---------------------------------------------------------------------------
resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

resource envStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: containerEnv
  name: fileShareName
  properties: {
    azureFile: {
      accountName: storageAccount.name
      accountKey: storageAccount.listKeys().keys[0].value
      shareName: fileShareName
      accessMode: 'ReadWrite'
    }
  }
}

// ---------------------------------------------------------------------------
// PostgreSQL Flexible Server — Burstable B1ms, cheapest managed tier
// ---------------------------------------------------------------------------
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    storage: {
      storageSizeGB: 32
      autoGrow: 'Disabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// Allow traffic from other Azure services (Container Apps egress has no
// stable outbound IP on consumption plan, so this is the simplest rule).
resource postgresFirewallAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: postgresDbName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ---------------------------------------------------------------------------
// Azure OpenAI — completion + embedding deployments
// ---------------------------------------------------------------------------
resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openAiName
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: 'Enabled'
  }
}

resource gptDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: gptDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  // Cognitive Services rejects parallel deployment creation — serialize via dependsOn.
  dependsOn: [ gptDeployment ]
  name: embeddingDeploymentName
  sku: {
    name: 'Standard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
  }
}

// ---------------------------------------------------------------------------
// Backend Container App — FastAPI + Gmail poller (single container)
// ---------------------------------------------------------------------------
var postgresConnectionString = 'postgresql+asyncpg://${postgresAdminLogin}:${postgresAdminPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${postgresDbName}?ssl=require'

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: backendAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${containerAppIdentity.id}': {}
    }
  }
  dependsOn: [
    acrPullRoleAssignment
    envStorage
    embeddingDeployment
    postgresDatabase
    postgresFirewallAllowAzure
  ]
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: [ '*' ]
          allowedMethods: [ 'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS' ]
          allowedHeaders: [ '*' ]
        }
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: containerAppIdentity.id
        }
      ]
      secrets: [
        {
          name: 'database-url'
          value: postgresConnectionString
        }
        {
          name: 'azure-openai-key'
          value: openAi.listKeys().key1
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'DATABASE_URL',                 secretRef: 'database-url' }
            { name: 'AZURE_OPENAI_API_KEY',         secretRef: 'azure-openai-key' }
            { name: 'AZURE_OPENAI_ENDPOINT',        value: openAi.properties.endpoint }
            { name: 'AZURE_OPENAI_API_VERSION',     value: '2024-10-21' }
            { name: 'AZURE_OPENAI_DEPLOYMENT',      value: gptDeploymentName }
            { name: 'AZURE_OPENAI_EMBED_API_KEY',   secretRef: 'azure-openai-key' }
            { name: 'AZURE_OPENAI_EMBED_ENDPOINT',  value: openAi.properties.endpoint }
            { name: 'AZURE_OPENAI_EMBED_DEPLOYMENT', value: embeddingDeploymentName }
            { name: 'AZURE_OPENAI_EMBED_DIMENSIONS', value: '3072' }
            { name: 'LANCEDB_PATH',                 value: '/app/data/lancedb' }
            { name: 'LOG_LEVEL',                    value: 'INFO' }
          ]
          volumeMounts: [
            {
              volumeName: 'lancedb-data'
              mountPath: '/app/data'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8000 }
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8000 }
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'lancedb-data'
          storageType: 'AzureFile'
          storageName: fileShareName
        }
      ]
      scale: {
        // The Gmail poller is an always-on background task, so min=1.
        // With Gmail disabled (the default in this demo) this could safely
        // drop to 0 with an HTTP scale rule.
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Static Web App — React frontend (Free tier)
// Free SKU is only available in a few regions; westeurope is the closest.
// ---------------------------------------------------------------------------
resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticWebAppName
  location: 'westeurope'
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    // Deploys happen via GitHub Actions using the deploy token, not via a
    // connected repository, so these fields stay empty.
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
  }
}

// ---------------------------------------------------------------------------
// Outputs — consumed by bootstrap.sh and seeded as CI secrets
// ---------------------------------------------------------------------------
output resourceGroupName          string = resourceGroup().name
output containerRegistryName      string = acr.name
output containerRegistryLoginServer string = acr.properties.loginServer
output containerAppName           string = backendApp.name
output containerAppFqdn           string = backendApp.properties.configuration.ingress.fqdn
output staticWebAppName           string = staticWebApp.name
output staticWebAppHostname       string = staticWebApp.properties.defaultHostname
output openAiEndpoint             string = openAi.properties.endpoint
output postgresFqdn               string = postgres.properties.fullyQualifiedDomainName
