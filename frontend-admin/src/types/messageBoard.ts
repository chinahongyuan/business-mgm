export interface MessageBoardRow {
  id: number;
  mobileUserId: number | null;
  ipRegion: string;
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
