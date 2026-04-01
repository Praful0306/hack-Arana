import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Rocket, EnvelopeSimple, Lock, Eye, EyeSlash, User, Code, Palette, ChartLineUp } from "@phosphor-icons/react";
import { useAuth, formatApiErrorDetail } from "../App";
import { toast } from "sonner";

const domains = [
  { id: "engineering", label: "Engineering", icon: Code, color: "#3B82F6", desc: "Build the product" },
  { id: "design", label: "Design", icon: Palette, color: "#EC4899", desc: "Shape the experience" },
  { id: "business", label: "Business", icon: ChartLineUp, color: "#10B981", desc: "Drive the growth" },
];

export default function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [domain, setDomain] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!domain) {
      setError("Please select your domain");
      return;
    }
    setLoading(true);
    setError("");

    try {
      await register(email, password, fullName, domain);
      toast.success("Account created! Let's set up your profile.");
      navigate("/onboarding");
    } catch (e) {
      setError(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0D0D1A] flex">
      {/* Left - Image */}
      <div className="hidden lg:block flex-1 relative">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent to-[#0D0D1A] z-10"></div>
        <img
          src="https://images.unsplash.com/photo-1568658176307-bfbd2873abda?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1NzZ8MHwxfHNlYXJjaHwxfHxzdHVkZW50JTIwc3RhcnR1cCUyMGZvdW5kZXJzJTIwY29sbGFib3JhdGluZ3xlbnwwfHx8fDE3NzUwMzQyMDB8MA&ixlib=rb-4.1.0&q=85"
          alt=""
          className="w-full h-full object-cover"
        />
      </div>

      {/* Right - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <Link to="/" className="flex items-center gap-2 mb-12 group">
            <div className="w-10 h-10 bg-gradient-to-br from-[#6C63FF] to-[#EC4899] rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
              <Rocket weight="fill" className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl">Antigravity</span>
          </Link>

          <h1 className="text-3xl font-bold mb-2">Create your account</h1>
          <p className="text-[#94A3B8] mb-8">Join the community and start building your startup</p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">Full Name</label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94A3B8]" size={20} />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Jane Smith"
                  className="w-full pl-12 pr-4 py-3 rounded-xl focus-ring"
                  required
                  data-testid="register-name-input"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Email</label>
              <div className="relative">
                <EnvelopeSimple className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94A3B8]" size={20} />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@university.edu"
                  className="w-full pl-12 pr-4 py-3 rounded-xl focus-ring"
                  required
                  data-testid="register-email-input"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94A3B8]" size={20} />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-12 pr-12 py-3 rounded-xl focus-ring"
                  minLength={6}
                  required
                  data-testid="register-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-white"
                >
                  {showPassword ? <EyeSlash size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-3">Your Domain</label>
              <div className="grid grid-cols-3 gap-3">
                {domains.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    onClick={() => setDomain(d.id)}
                    className={`p-4 rounded-xl border-2 transition-all text-center ${
                      domain === d.id
                        ? "border-[#6C63FF] bg-[#6C63FF]/10"
                        : "border-white/10 hover:border-white/30"
                    }`}
                    data-testid={`domain-${d.id}-btn`}
                  >
                    <d.icon
                      weight="duotone"
                      size={28}
                      className="mx-auto mb-2"
                      style={{ color: d.color }}
                    />
                    <div className="font-medium text-sm">{d.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-4 flex items-center justify-center gap-2 disabled:opacity-50"
              data-testid="register-submit-btn"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          <p className="text-center mt-8 text-[#94A3B8]">
            Already have an account?{" "}
            <Link to="/login" className="text-[#6C63FF] hover:underline" data-testid="register-login-link">
              Sign in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
