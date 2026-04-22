export type ProductCategory = {
  id: number;
  typeCode: number;
  name: string;
};

export type ProductTag = {
  id: number;
  name: string;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type ProductListItem = {
  id: number;
  name: string;
  coverImage: string | null;
  city: string | null;
  district: string | null;
  visitCount: number;
  address: string | null;
  status: string;
  sortOrder: number;
  flag1: boolean;
  flag2: boolean;
  /** 显示隐藏（扩展 flag3） */
  flag3: boolean;
  categoryName?: string;
  createdAt?: string | null;
  /** 回收站列表返回 */
  deletedAt?: string | null;
};

export type ProductDetail = ProductListItem & {
  categoryId: number;
  typeCode: number | null;
  province: string | null;
  longitude: number | null;
  latitude: number | null;
  starRating: number;
  price: number;
  sortOrder: number;
  detailHtml: string;
  tagIds: number[];
};
