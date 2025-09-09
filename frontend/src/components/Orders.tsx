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
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<Order>>({});

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

  const startEdit = (order: Order) => {
    setEditingId(order.id);
    setEditData({ ...order });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditData({});
  };

  const saveEdit = async (orderId: string) => {
    await api.put(`/api/orders/edit/${orderId}`, editData);
    setEditingId(null);
    setEditData({});
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
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id}>
              <td>
                {editingId === o.id ? (
                  <input
                    value={editData.message || ""}
                    onChange={(e) =>
                      setEditData({ ...editData, message: e.target.value })
                    }
                  />
                ) : (
                  o.message
                )}
              </td>
              <td>{o.orderType}</td>
              <td>
                {editingId === o.id ? (
                  <select
                    value={editData.buySell || ""}
                    onChange={(e) =>
                      setEditData({ ...editData, buySell: e.target.value })
                    }
                  >
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                ) : (
                  o.buySell
                )}
              </td>
              <td>
                {editingId === o.id ? (
                  <input
                    type="number"
                    value={editData.quantity || 0}
                    onChange={(e) =>
                      setEditData({
                        ...editData,
                        quantity: Number(e.target.value),
                      })
                    }
                  />
                ) : (
                  o.quantity
                )}
              </td>
              <td>
                {editingId === o.id ? (
                  <input
                    type="number"
                    value={editData.price || 0}
                    onChange={(e) =>
                      setEditData({
                        ...editData,
                        price: Number(e.target.value),
                      })
                    }
                  />
                ) : (
                  o.price
                )}
              </td>
              <td>{o.basis}</td>
              <td>{o.strategyDisplayName}</td>
              <td>{o.contractId}</td>
              <td>{o.expiryDate}</td>
              <td>
                {editingId === o.id ? (
                  <>
                    <button
                      className="bg-green-500 text-white px-2 py-1 mr-2 rounded"
                      onClick={() => saveEdit(o.id)}
                    >
                      Save
                    </button>
                    <button
                      className="bg-gray-400 text-white px-2 py-1 rounded"
                      onClick={cancelEdit}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    className="bg-blue-500 text-white px-2 py-1 rounded"
                    onClick={() => startEdit(o)}
                  >
                    Edit
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
