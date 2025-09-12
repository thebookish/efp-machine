import { useState } from "react";
import axios from "axios";

const UploadJson = () => {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");

  const handleUpload = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await axios.post("http://localhost:8000/api/orders/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessage(`Inserted: ${resp.data.inserted}`);
    } catch (e: any) {
      setMessage(`Error: ${e.response?.data?.detail || e.message}`);
    }
  };

  return (
    <div className="p-4 border rounded">
      <input
        type="file"
        accept=".json"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button
        onClick={handleUpload}
        className="ml-2 px-4 py-2 bg-blue-500 text-white rounded"
      >
        Upload JSON
      </button>
      {message && <p className="mt-2">{message}</p>}
    </div>
  );
};

export default UploadJson;
