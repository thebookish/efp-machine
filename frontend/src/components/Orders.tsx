import React, { useState, useEffect } from "react";
import axios from "axios";

const api = axios.create({
  baseURL: "https://efp-machine-2.onrender.com", // change to backend
});

type Order = {
  id: string;
  message: string;
  orderType: string;
  buySell: string;
  quantity: number;
  price: number;
  basis: number;
  strategyDisplayName: string;
  contractId: string;
  expiryDate: string;
  created_at: string;
};

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);

  const fetchOrders = async () => {
    const { data } = await api.get("/api/orders/list");
    setOrders(data);
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    await api.post("/api/orders/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    await fetchOrders();
  };

  return (
    <div className="p-6">
      <h1 className="text-xl font-bold mb-4">Orders</h1>
      {/* <input type="file" accept=".json" onChange={handleUpload} /> */}
      <table className="min-w-full border mt-4">
        <thead>
          <tr>
            <th>Message</th>
            <th>OrderType</th>
            <th>Buy/Sell</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Basis</th>
            <th>StrategyDisplayName</th>
            <th>ContractId</th>
            <th>Expiry</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id}>
              <td>{o.message}</td>
              <td>{o.orderType}</td>
              <td>{o.buySell}</td>
              <td>{o.quantity}</td>
              <td>{o.price}</td>
              <td>{o.basis}</td>
              <td>{o.strategyDisplayName}</td>
              <td>{o.contractId}</td>
              <td>{o.expiryDate}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
