import { httpClient } from "./httpClient";

export const orderApi = {
  getOrders: () => httpClient.get("/orders"),
  getOrderById: (id: string) => httpClient.get(`/orders/${id}`),
  createOrder: (data: unknown) => httpClient.post("/orders", data),
  updateOrder: (id: string, data: unknown) =>
    httpClient.patch(`/orders/${id}`, data),
  deleteOrder: (id: string) => httpClient.delete(`/orders/${id}`),
};
