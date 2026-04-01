import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Rocket, Users, Brain, ArrowRight, Sparkle, Code, Palette, ChartLineUp } from "@phosphor-icons/react";

const stats = [
  { value: "120+", label: "Projects Launched" },
  { value: "48", label: "Active Teams" },
  { value: "310+", label: "Milestones Hit" },
];

const features = [
  {
    icon: Brain,
    title: "AI-Powered Matching",
    description: "Our intelligent algorithm finds you the perfect co-founders based on skills, availability, and working style.",
    color: "#6C63FF",
  },
  {
    icon: Users,
    title: "Cross-Domain Teams",
    description: "Engineering meets Design meets Business. Build diverse teams that can tackle any challenge.",
    color: "#EC4899",
  },
  {
    icon: Rocket,
    title: "Startup Tools",
    description: "AI co-founder chat, roadmap generation, pitch decks, and readiness scoring — all built in.",
    color: "#10B981",
  },
];

const domains = [
  { name: "Engineering", icon: Code, color: "#3B82F6" },
  { name: "Design", icon: Palette, color: "#EC4899" },
  { name: "Business", icon: ChartLineUp, color: "#10B981" },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#0D0D1A] overflow-hidden">
      {/* Navbar */}
      <nav className="glass fixed top-0 w-full z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-10 h-10 bg-gradient-to-br from-[#6C63FF] to-[#EC4899] rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
              <Rocket weight="fill" className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight">Antigravity</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/login" className="btn-secondary" data-testid="landing-login-btn">
              Log in
            </Link>
            <Link to="/register" className="btn-primary flex items-center gap-2" data-testid="landing-register-btn">
              Get Started <ArrowRight weight="bold" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative min-h-screen flex items-center pt-20">
        {/* Background */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#6C63FF] rounded-full blur-[150px] opacity-20"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#EC4899] rounded-full blur-[150px] opacity-20"></div>
          <img
            src="https://images.unsplash.com/photo-1767481626894-bab78ae919be?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzZ8MHwxfHNlYXJjaHwzfHxhYnN0cmFjdCUyMGRhcmslMjBwdXJwbGUlMjBuZW9uJTIwc3BhY2V8ZW58MHx8fHwxNzc1MDM0MjA1fDA&ixlib=rb-4.1.0&q=85"
            alt=""
            className="absolute inset-0 w-full h-full object-cover opacity-10"
          />
        </div>

        <div className="relative max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <span className="overline text-[#6C63FF] mb-4 block">Student Startup Incubator</span>
            <h1 className="text-5xl lg:text-7xl font-bold leading-tight mb-6">
              Break the silo.
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#6C63FF] via-[#EC4899] to-[#10B981]">
                Build the startup.
              </span>
            </h1>
            <p className="text-xl text-[#94A3B8] mb-8 max-w-lg">
              Connect with co-founders from engineering, design, and business. Get AI-powered tools to turn your idea
              into reality.
            </p>
            <div className="flex items-center gap-4">
              <Link to="/register" className="btn-primary text-lg px-8 py-4 flex items-center gap-2" data-testid="hero-cta-btn">
                Start Building <Sparkle weight="fill" />
              </Link>
              <Link to="/login" className="btn-secondary text-lg px-8 py-4">
                I have an account
              </Link>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-8 mt-12 pt-8 border-t border-white/10">
              {stats.map((stat, i) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + i * 0.1 }}
                >
                  <div className="font-mono text-3xl font-bold text-[#6C63FF]">{stat.value}</div>
                  <div className="text-sm text-[#94A3B8]">{stat.label}</div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Domain Cards */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="relative hidden lg:block"
          >
            <div className="relative">
              {domains.map((domain, i) => (
                <motion.div
                  key={domain.name}
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + i * 0.15 }}
                  className="glow-card rounded-2xl p-6 mb-4"
                  style={{
                    marginLeft: i * 40,
                    borderColor: `${domain.color}30`,
                  }}
                >
                  <div className="flex items-center gap-4">
                    <div
                      className="w-14 h-14 rounded-xl flex items-center justify-center"
                      style={{ background: `${domain.color}20` }}
                    >
                      <domain.icon weight="duotone" size={28} style={{ color: domain.color }} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">{domain.name}</h3>
                      <p className="text-sm text-[#94A3B8]">Find your perfect match</p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <span className="overline text-[#6C63FF] mb-4 block">Why Antigravity?</span>
            <h2 className="text-4xl font-bold">Everything you need to launch</h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="glow-card rounded-2xl p-8"
              >
                <div
                  className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6"
                  style={{ background: `${feature.color}20` }}
                >
                  <feature.icon weight="duotone" size={32} style={{ color: feature.color }} />
                </div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-[#94A3B8] leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Team Image */}
      <section className="py-24 relative">
        <div className="max-w-6xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="relative rounded-3xl overflow-hidden"
          >
            <img
              src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHwzfHxzdGFydHVwJTIwdGVhbSUyMGNvZGluZyUyMGNvbGxhYm9yYXRpbmd8ZW58MHx8fHwxNzc1MDM0MjA1fDA&ixlib=rb-4.1.0&q=85"
              alt="Team collaborating"
              className="w-full h-[400px] object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#0D0D1A] via-transparent to-transparent"></div>
            <div className="absolute bottom-8 left-8 right-8">
              <h3 className="text-2xl font-bold mb-2">Built for students, by students</h3>
              <p className="text-[#94A3B8]">
                Join a community of ambitious builders turning ideas into real companies.
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 relative">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-4xl font-bold mb-6">Ready to find your co-founder?</h2>
            <p className="text-xl text-[#94A3B8] mb-8">
              Create your profile, add your skills, and let our AI match you with the perfect team.
            </p>
            <Link to="/register" className="btn-primary text-lg px-10 py-4 inline-flex items-center gap-2" data-testid="cta-register-btn">
              Join Antigravity <ArrowRight weight="bold" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Rocket weight="fill" className="w-5 h-5 text-[#6C63FF]" />
            <span className="font-semibold">Antigravity</span>
          </div>
          <p className="text-sm text-[#94A3B8]">© 2024 Antigravity. Built for dreamers.</p>
        </div>
      </footer>
    </div>
  );
}
