// Where "‹ Back" on a visit page returns to: the list screen the rep opened the
// customer from (Needs attention or All customers). Remembered for the tab.

import { useEffect, useState } from "react";

export const SCREEN = { ATTENTION: "/", CUSTOMERS: "/customers" };
// Not a list screen: "back" from a customer created here goes to All customers.
export const NEW_CUSTOMER = "/customers/new";
// View Products — stock lookup, not a customer list, so "back" from a visit
// never lands here. The code goes in the query string: some contain "/" or "+".
export const PRODUCTS = "/products";
export const productHref = (code) => `${PRODUCTS}/item?code=${encodeURIComponent(code)}`;
const BACK_KEY = "searay.back";

export function useRememberScreen(path) {
  useEffect(() => {
    try {
      sessionStorage.setItem(BACK_KEY, path);
    } catch {}
  }, [path]);
}

export function useBackHref() {
  const [href, setHref] = useState(SCREEN.ATTENTION);
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(BACK_KEY);
      if (Object.values(SCREEN).includes(saved)) setHref(saved);
    } catch {}
  }, []);
  return href;
}
