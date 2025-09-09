import React, { useState, useEffect } from "react";
import axios from "axios";

const api = axios.create({
  baseURL: "https://efp-machine-2.onrender.com", 
  headers: { "Content-Type": "application/json" },
});

type Order = {
  id: string;
  client_provided_id: string;
  symbol: string;
  expiry: string;
  side: string;
  quantity: number;
  price: number;
  basis: number;
  created_at: string;
};

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch orders from backend
  const fetchOrders = async () => {
    try {
      const { data } = await api.get<Order[]>("/api/orders/list");
      setOrders(data);
    } catch (err) {
      console.error("Failed to fetch orders", err);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  // Handle JSON file upload
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;

    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    try {
      await api.post("/api/orders/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await fetchOrders(); // refresh after upload
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-xl font-bold mb-4">Orders</h1>

      {/* Orders table */}
      <table className="min-w-full border border-gray-300">
        <thead className="bg-black">
          <tr>
            <th className="border p-2">ID</th>
            <th className="border p-2">Symbol</th>
            <th className="border p-2">Expiry</th>
            <th className="border p-2">Side</th>
            <th className="border p-2">Quantity</th>
            <th className="border p-2">Price</th>
            <th className="border p-2">Basis</th>
            <th className="border p-2">Created At</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id}>
              <td className="border p-2">{o.client_provided_id}</td>
              <td className="border p-2">{o.symbol}</td>
              <td className="border p-2">{o.expiry}</td>
              <td className="border p-2">{o.side}</td>
              <td className="border p-2">{o.quantity}</td>
              <td className="border p-2">{o.price}</td>
              <td className="border p-2">{o.basis}</td>
              <td className="border p-2">
                {new Date(o.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
