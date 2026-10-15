import Link from "next/link";
import { UserIcon } from "@/components/ui/icons";

/** Placeholder until sessions exist: a plain link to the login screen. */
export function AccountButton() {
  return (
    <Link
      href="/login"
      aria-label="Account: sign in"
      className="t-fast grid size-10 place-items-center rounded-full border border-line bg-surface text-muted hover:text-fg"
    >
      <UserIcon />
    </Link>
  );
}
