export function refund(orderId: string) {
  return { orderId, status: "refund_requested" };
}
