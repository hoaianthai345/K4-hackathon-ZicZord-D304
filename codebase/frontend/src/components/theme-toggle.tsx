"use client";

import { Moon, Sun } from "@phosphor-icons/react";

export function ThemeToggle() {
  function toggle() {
    const current =
      document.documentElement.dataset.theme ??
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current !== "dark";
    document.documentElement.dataset.theme = next ? "dark" : "light";
    localStorage.setItem("recall-theme", next ? "dark" : "light");
  }

  return (
    <button
      type="button"
      onClick={toggle}
      className="icon-button"
      aria-label="Đổi chế độ sáng tối"
      title="Đổi chế độ sáng tối"
    >
      <Sun className="theme-icon-light" size={17} weight="bold" />
      <Moon className="theme-icon-dark" size={17} weight="bold" />
    </button>
  );
}
