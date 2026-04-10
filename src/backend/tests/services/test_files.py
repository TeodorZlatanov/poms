from services.files import detect_file_type, extract_text_from_csv, extract_text_from_xlsx


class TestDetectFileType:
    def test_csv_by_content_type(self):
        result = detect_file_type("data.csv", "text/csv", b"col1,col2\nval1,val2")
        assert result == "csv"

    def test_csv_by_extension(self):
        result = detect_file_type("data.csv", "application/octet-stream", b"col1,col2\nval1,val2")
        assert result == "csv"

    def test_xlsx_by_content_type(self):
        ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        result = detect_file_type("data.xlsx", ct, b"")
        assert result == "xlsx"

    def test_xlsx_by_extension(self):
        result = detect_file_type("data.xlsx", "application/octet-stream", b"")
        assert result == "xlsx"

    def test_xls_by_extension(self):
        result = detect_file_type("data.xls", "application/octet-stream", b"")
        assert result == "xlsx"

    def test_image_by_content_type(self):
        result = detect_file_type("scan.png", "image/png", b"\x89PNG")
        assert result == "image"

    def test_image_by_extension(self):
        result = detect_file_type("scan.jpg", "application/octet-stream", b"\xff\xd8\xff")
        assert result == "image"


class TestExtractTextFromCsv:
    async def test_basic_csv(self):
        csv_data = b"Item,Quantity,Price\nWidget,10,12.50\nGadget,5,25.00"
        result = await extract_text_from_csv(csv_data)
        assert "Widget" in result
        assert "12.5" in result
        assert "Gadget" in result

    async def test_single_column_csv(self):
        csv_data = b"Name\nAlice\nBob"
        result = await extract_text_from_csv(csv_data)
        assert "Alice" in result
        assert "Bob" in result


class TestExtractTextFromXlsx:
    async def test_basic_xlsx(self):
        import io

        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "PO Data"
        ws.append(["Item", "Quantity", "Price"])
        ws.append(["Sensor", 50, 12.50])
        ws.append(["Belt", 100, 17.50])
        buf = io.BytesIO()
        wb.save(buf)

        result = await extract_text_from_xlsx(buf.getvalue())
        assert "PO Data" in result
        assert "Sensor" in result
        assert "Belt" in result
