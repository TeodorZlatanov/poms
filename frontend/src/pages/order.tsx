import { useParams } from "react-router";

export function OrderPage() {
  const { id } = useParams();
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">Order Detail</h1>
      <p className="mt-2 text-muted">Order ID: {id}</p>
    </div>
  );
}
