export interface MobileUserRow {
  id: number;
  ip: string | null;
  ipRegion: string | null;
  status: "normal" | "disabled";
  userRegion: string | null;
  lastLoginAt: string | null;
  isOnline: boolean;
}

export interface MobileUserMessage {
  id: number;
  productId: number;
  content: string;
  auditStatus: string;
  createdAt: string | null;
  ipRegion: string;
}

export interface MobileUserDetail {
  id: number;
  visitorKey: string | null;
  ip: string | null;
  ipRegion: string | null;
  status: string;
  userRegion: string | null;
  lastLoginAt: string | null;
  visitCount: number;
  lastProductId: number | null;
  lastMessageId: number | null;
  pwdFailCount: number;
  lastSeenAt: string | null;
  isOnline: boolean;
  createdAt: string | null;
  updatedAt: string | null;
  messages: MobileUserMessage[];
}
