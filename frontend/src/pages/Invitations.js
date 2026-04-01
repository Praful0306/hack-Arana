import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { API, useAuth, formatApiErrorDetail } from "../App";
import { toast } from "sonner";
import { ArrowLeft, EnvelopeOpen, Check, X } from "@phosphor-icons/react";

export default function Invitations() {
  const { user } = useAuth();
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [responding, setResponding] = useState(null);

  useEffect(() => { fetchInvitations(); }, []);

  const fetchInvitations = async () => {
    try {
      const { data } = await axios.get(`${API}/invitations`, { withCredentials: true });
      setInvitations(data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const respond = async (id, accept) => {
    setResponding(id);
    try {
      await axios.post(`${API}/invitations/${id}/respond?accept=${accept}`, {}, { withCredentials: true });
      setInvitations(invitations.filter((i) => i.id !== id));
      toast.success(accept ? "Invitation accepted!" : "Invitation declined");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); } finally { setResponding(null); }
  };

  return (
    <div className="min-h-screen bg-[#0D0D1A] py-12 px-6">
      <div className="max-w-2xl mx-auto">
        <Link to="/dashboard" className="flex items-center gap-2 text-[#94A3B8] hover:text-white mb-8 transition-colors"><ArrowLeft size={20} /> Back to Dashboard</Link>
        <h1 className="text-2xl font-bold mb-8">Team Invitations</h1>

        {loading ? (
          <div className="space-y-4">{[1, 2, 3].map((i) => <div key={i} className="h-24 bg-[#141428] rounded-xl animate-pulse"></div>)}</div>
        ) : invitations.length === 0 ? (
          <div className="text-center py-20">
            <EnvelopeOpen size={64} className="mx-auto mb-4 text-[#94A3B8] opacity-50" />
            <p className="text-[#94A3B8]">No pending invitations</p>
          </div>
        ) : (
          <div className="space-y-4">
            {invitations.map((inv) => (
              <motion.div key={inv.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glow-card rounded-2xl p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold mb-1">{inv.project_title}</h3>
                    <p className="text-sm text-[#94A3B8]">Invited by {inv.inviter_name}</p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => respond(inv.id, false)} disabled={responding === inv.id} className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors" data-testid={`decline-${inv.id}`}>
                      <X size={20} />
                    </button>
                    <button onClick={() => respond(inv.id, true)} disabled={responding === inv.id} className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors" data-testid={`accept-${inv.id}`}>
                      {responding === inv.id ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-emerald-400"></div> : <Check size={20} />}
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
