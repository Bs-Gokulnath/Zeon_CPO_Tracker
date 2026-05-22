export interface PageInfo {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> {
  data:  T[];
  page:  PageInfo;
  stats: import("./station").StationAggStats;
}

export interface ApiError {
  detail: string;
}
