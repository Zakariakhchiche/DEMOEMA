import { motion } from 'framer-motion';

export function SkeletonCard() {
  return (
    <motion.div 
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="p-10 rounded-[3rem] bg-black/40 border border-white/10 relative overflow-hidden backdrop-blur-3xl shadow-2xl"
    >
      <div className="animate-pulse">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center gap-5 mb-5">
              <div className="w-16 h-16 rounded-[1.5rem] bg-white/5 border border-white/10">
                <div className="w-7 h-7 bg-white/10 rounded m-auto mt-4" />
              </div>
              <div>
                <div className="w-48 h-8 bg-white/10 rounded mb-2" />
                <div className="flex gap-3 items-center">
                  <div className="w-24 h-6 bg-white/10 rounded-xl" />
                  <div className="w-20 h-4 bg-white/10 rounded" />
                </div>
              </div>
            </div>
            
            <div className="flex flex-wrap gap-3 mt-8">
              <div className="w-32 h-8 bg-white/5 rounded-2xl" />
              <div className="w-36 h-8 bg-white/5 rounded-2xl" />
              <div className="w-28 h-8 bg-white/5 rounded-2xl" />
            </div>
          </div>
          
          <div className="flex flex-col items-end">
            <div className="w-16 h-16 bg-white/10 rounded mb-3" />
            <div className="w-20 h-4 bg-white/10 rounded" />
          </div>
        </div>

        <div className="mt-10 pt-8 border-t border-white/[0.05] flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex gap-8 sm:gap-12">
            <div className="space-y-1.5">
              <div className="w-20 h-4 bg-white/10 rounded" />
              <div className="w-24 h-6 bg-white/10 rounded" />
            </div>
            <div className="space-y-1.5">
              <div className="w-24 h-4 bg-white/10 rounded" />
              <div className="w-20 h-6 bg-white/10 rounded" />
            </div>
          </div>
          
          <div className="w-32 h-12 bg-white/10 rounded-2xl" />
        </div>
      </div>
    </motion.div>
  );
}
