"use client";
import { Suspense } from "react";
import LibraryPage from "@/components/LibraryPage";
export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><LibraryPage kind="spells" /></Suspense>; }
