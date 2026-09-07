import Hero from "@/components/Hero";
import Sidebar from "@/components/Sidebar";

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
