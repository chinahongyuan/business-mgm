export interface MessageBoardRow {
  id: number;
  mobileUserId: number | null;
  /** 列表：关联 app_mobile_user.ip；管理员留言为「管理后台」等 */
  mobileUserIp: string;
  productId: number;
  productName: string;
  coverImage: string | null;
  auditStatus: "pending" | "approved";
  createdByAdmin: boolean;
  createdAt: string | null;
  contentPreview?: string;
}

export interface MessageBoardDetail extends MessageBoardRow {
  content: string;
}

export interface ProductOption {
  id: number;
  name: string;
  coverImage: string | null;
}
