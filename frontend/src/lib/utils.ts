import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind class-name combiner. Standard shadcn boilerplate. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
