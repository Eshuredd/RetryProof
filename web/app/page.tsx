import { Header } from "@/components/header";
import { Hero } from "@/components/hero";
import { MetricsStrip } from "@/components/metrics-strip";
import { VerificationProof } from "@/components/verification-proof";
import { ContractProof } from "@/components/contract-proof";
import { Workflow } from "@/components/workflow";
import { EvidenceViewer } from "@/components/evidence-viewer";
import { Footer } from "@/components/footer";

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <Hero />
        <MetricsStrip />
        <VerificationProof />
        <ContractProof />
        <Workflow />
        <EvidenceViewer />
      </main>
      <Footer />
    </div>
  );
}
