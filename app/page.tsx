import Hero from "@/components/Hero";
import Sidebar from "@/components/Sidebar";
import Image from "next/image";

export default function Home() {
  return (
    <>
      <div className="flex flew-row">
        <Sidebar/>
        <Hero/>
      </div>
    </>
  );
}
