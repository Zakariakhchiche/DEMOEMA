import { motion } from 'framer-motion';

export function SkeletonKPI() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-8 rounded-[2.5rem] bg-black/40 border border-white/10 backdrop-blur-2xl"
    >
      <div className="animate-pulse">
        <div className="flex justify-between items-start mb-8">
          <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10">
            <div className="w-6 h-6 bg-white/10 rounded" />
          </div>
          <div className="w-12 h-5 bg-white/10 rounded-xl" />
        </div>
        <div className="text-4xl font-black text-white mb-2 tracking-tighter">
          <div className="w-20 h-10 bg-white/10 rounded" />
        </div>
        <div className="text-[10px] font-black text-gray-500 uppercase tracking-widest">
          <div className="w-24 h-4 bg-white/10 rounded" />
        </div>
      </div>
    </motion.div>
  );
}
