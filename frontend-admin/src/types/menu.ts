export type MenuNode = {
  id: number;
  parentId: number | null;
  title: string;
  path: string | null;
  icon: string | null;
  sortOrder: number;
  isActive: boolean;
  children?: MenuNode[];
};
