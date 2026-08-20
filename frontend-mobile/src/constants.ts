// Bump the namespace after the production database was recreated so old
// browsers do not enter the protected routes with an orphaned visitor key.
export const STORAGE_VISITOR_KEY = "bm_mobile_visitor_key_v2";
