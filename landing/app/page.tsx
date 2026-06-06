import Nav from "./components/Nav";
import Hero from "./components/Hero";
import About from "./components/About";
import Features from "./components/Features";
import Architecture from "./components/Architecture";
import Team from "./components/Team";
import Supervisor from "./components/Supervisor";
import Footer from "./components/Footer";

export default function Home() {
  return (
    <main className="relative">
      <Nav />
      <Hero />
      <About />
      <Features />
      <Architecture />
      <Team />
      <Supervisor />
      <Footer />
    </main>
  );
}
