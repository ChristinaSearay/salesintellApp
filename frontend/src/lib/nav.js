// Where "‹ Back" on a visit page returns to: the list screen the rep opened the
// customer from (Needs attention or All customers). Remembered for the tab.

import { useEffect, useState } from "react";

export const SCREEN = { ATTENTION: "/", CUSTOMERS: "/customers" };
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
