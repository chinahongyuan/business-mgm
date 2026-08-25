import assert from "node:assert/strict";
import { canOpenDistrictFilter } from "../src/utils/productFilter.ts";

assert.equal(canOpenDistrictFilter(""), false);
assert.equal(canOpenDistrictFilter("   "), false);
assert.equal(canOpenDistrictFilter("北京市"), true);

console.log("productFilter tests passed");
