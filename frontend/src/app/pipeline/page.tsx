"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Layers, Plus, MoreHorizontal, Activity, Target, Zap, Clock, ShieldCheck, ArrowRight, Radio, Filter, Sparkles, ChevronRight } from "lucide-react";
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd";

// --- Types ---
interface PipelineCard {
  id: string;
  name: string;
  sector: string;
  score: number;
  tags: string[];
  priority: "high" | "medium" | "low";
}

interface Column {
  id: string;
  title: string;
  color: string;
  cards: PipelineCard[];
}

// --- Initial Data ---
const initialData: Column[] = [
  {
    id: "identification",
    title: "Identification",
    color: "border-gray-500",
    cards: [
      { id: "c1", name: "Horizon Solar", sector: "Renewable Energy", score: 82, tags: ["Scale-up", "US"], priority: "medium" },
      { id: "c2", name: "CyberGrid", sector: "SaaS", score: 71, tags: ["Profitability focus"], priority: "low" },
    ],
  },
  {
    id: "qualification",
    title: "Qualification",
    color: "border-indigo-500",
    cards: [
      { id: "c3", name: "TechFlow Industrials", sector: "Industrial Tech", score: 89, tags: ["Warm Intro", "3-6m Window"], priority: "high" },
      { id: "c4", name: "Aetherial SA", sector: "Renewable Energy", score: 76, tags: ["Succession"], priority: "high" },
    ],
  },
  {
    id: "pathing",
    title: "Relationship Pathing",
    color: "border-purple-500",
    cards: [
      { id: "c5", name: "NexSphere Healthcare", sector: "MedTech", score: 68, tags: ["Carve-out"], priority: "medium" },
    ],
  },
  {
    id: "outreach",
    title: "Active Outreach",
    color: "border-amber-500",
    cards: [
      { id: "c6", name: "Blue Harbor Log", sector: "Logistics", score: 94, tags: ["Proprietary"], priority: "high" },
    ],
  },
  {
    id: "closing",
    title: "Closing",
    color: "border-emerald-500",
    cards: [],
  },
];

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function PipelinePage() {
  const [columns, setColumns] = useState<Column[]>([]);
  const [isClient, setIsClient] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fix Hydration mismatch for DND
  useEffect(() => {
    setIsClient(true);
    setLoading(true);
    fetch(`${API_URL}/api/pipeline`)
      .then(res => res.json())
      .then(json => {
        setColumns(json.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch pipeline:", err);
        setLoading(false);
      });
  }, []);

  const onDragEnd = (result: DropResult) => {
    const { destination, source } = result;

    if (!destination) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index) return;

    const sourceColIndex = columns.findIndex(col => col.id === source.droppableId);
    const destColIndex = columns.findIndex(col => col.id === destination.droppableId);

    const sourceCol = columns[sourceColIndex];
    const destCol = columns[destColIndex];

    const sourceCards = Array.from(sourceCol.cards);
    const [movedCard] = sourceCards.splice(source.index, 1);

    if (sourceColIndex === destColIndex) {
      sourceCards.splice(destination.index, 0, movedCard);
      const newColumns = [...columns];
      newColumns[sourceColIndex] = { ...sourceCol, cards: sourceCards };
      setColumns(newColumns);
    } else {
      const destCards = Array.from(destCol.cards);
      destCards.splice(destination.index, 0, movedCard);
      const newColumns = [...columns];
      newColumns[sourceColIndex] = { ...sourceCol, cards: sourceCards };
      newColumns[destColIndex] = { ...destCol, cards: destCards };
      setColumns(newColumns);
    }
  };

  if (!isClient) return null;

  return (
    <div className="flex flex-col gap-10 w-full max-w-full mx-auto h-[calc(100vh-8rem)] py-4 overflow-hidden relative">
      {/* Header */}
      <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 px-4 shrink-0">
        <div>
          <h1 className="text-3xl md:text-5xl font-black tracking-tighter text-white mb-3 flex flex-wrap items-center gap-4 sm:gap-5">
            Pipeline Command
            <div className="flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] text-emerald-400 font-black uppercase tracking-[0.2em]">
               <Radio size={14} className="animate-pulse" /> Live Flow
            </div>
          </h1>
          <p className="text-gray-400 text-base md:text-lg font-medium max-w-2xl leading-relaxed">
            Active origination lifecycle management. Coordinating <span className="text-white">anomaly detection</span> to deal execution.
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-4 w-full lg:w-auto items-center">
           <div className="hidden sm:flex -space-x-3 items-center mr-4">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="w-8 h-8 lg:w-10 lg:h-10 rounded-xl lg:rounded-2xl bg-black border-2 border-[#0a0a0a] ring-2 ring-white/5 flex items-center justify-center text-[10px] lg:text-[11px] font-black text-white bg-gradient-to-br from-white/10 to-transparent backdrop-blur-xl">
                   {String.fromCharCode(64 + i)}
                </div>
              ))}
              <div className="w-8 h-8 lg:w-10 lg:h-10 rounded-xl lg:rounded-2xl bg-indigo-600 border-2 border-[#0a0a0a] ring-2 ring-indigo-500/30 flex items-center justify-center text-[9px] lg:text-[10px] font-black text-white relative z-10 shadow-lg">
                 +12
              </div>
           </div>
           <div className="flex gap-3 w-full sm:w-auto">
             <button className="flex-1 sm:flex-none px-6 py-3 rounded-2xl bg-white/[0.03] border border-white/10 text-[11px] font-black uppercase tracking-widest text-white hover:bg-white/10 transition-all flex items-center justify-center gap-3 backdrop-blur-xl">
               <Filter size={16} className="text-indigo-400" /> <span className="sm:hidden lg:inline">Config</span>
             </button>
             <button className="flex-1 sm:flex-none px-6 py-3 rounded-2xl bg-indigo-600 text-white shadow-2xl shadow-indigo-600/30 hover:bg-indigo-50 transition-all flex items-center justify-center gap-3 font-black text-[11px] uppercase tracking-widest active:scale-95">
               <Sparkles size={16} /> Force Sync
             </button>
           </div>
        </div>
      </header>

      {/* Board Layout */}
      <div className="flex-1 overflow-x-auto pb-10 scrollbar-hide px-4">
        <DragDropContext onDragEnd={onDragEnd}>
          <div className="flex gap-8 h-full w-max min-w-full">
             {columns.map((column) => (
              <div key={column.id} className="w-[300px] sm:w-[340px] flex flex-col h-full bg-black/40 rounded-[2.5rem] sm:rounded-[3rem] border border-white/10 shadow-2xl overflow-hidden backdrop-blur-3xl group/col shrink-0">
                
                {/* Stage Header */}
                <div className="p-8 pb-5 flex items-center justify-between relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent opacity-0 group-hover/col:opacity-100 transition-opacity" />
                  <div className="flex items-center gap-4">
                    <div className={`w-2.5 h-2.5 rounded-full shadow-[0_0_10px_rgba(79,70,229,0.5)] ${
                      column.id === 'closing' ? 'bg-emerald-500' : 
                      column.id === 'outreach' ? 'bg-amber-500' : 
                      column.id === 'pathing' ? 'bg-purple-500' :
                      'bg-indigo-500'
                    }`} />
                    <h3 className="font-black text-white text-[11px] uppercase tracking-[0.3em]">{column.title}</h3>
                  </div>
                  <span className="px-4 py-1.5 rounded-2xl bg-white/5 border border-white/10 text-gray-400 text-[10px] font-black">{column.cards.length}</span>
                </div>

                {/* Drop Area */}
                <Droppable droppableId={column.id}>
                  {(provided, snapshot) => (
                    <div 
                      {...provided.droppableProps}
                      ref={provided.innerRef}
                      className={`flex-1 p-6 overflow-y-auto flex flex-col gap-6 transition-all custom-scrollbar
                        ${snapshot.isDraggingOver ? "bg-white/[0.04]" : ""}
                      `}
                    >
                      {column.cards.map((card, index) => (
                        <Draggable key={card.id} draggableId={card.id} index={index}>
                          {(provided, snapshot) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              className={`group p-8 rounded-[2.5rem] bg-white/[0.03] border border-white/10 hover:border-indigo-500/40 cursor-grab active:cursor-grabbing transition-all shadow-xl backdrop-blur-2xl relative overflow-hidden
                                ${snapshot.isDragging ? "rotate-2 scale-[1.05] shadow-[0_40px_80px_rgba(0,0,0,0.8)] !border-indigo-500/60 !bg-indigo-500/10 z-[1000]" : ""}
                              `}
                            >
                              <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-10 transition-opacity">
                                 <MoreHorizontal size={40} />
                              </div>

                              <div className="flex justify-between items-start mb-6">
                                <div className="flex gap-2">
                                  <span className="px-2.5 py-1 rounded-xl text-[9px] font-black tracking-widest uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/10">
                                    {card.sector}
                                  </span>
                                  {card.priority === 'high' && (
                                    <div className="px-2 py-1 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center gap-1.5">
                                       <Zap size={10} className="text-rose-500" />
                                       <span className="text-[8px] font-black text-rose-500 uppercase tracking-tighter">Priority</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                              
                              <h4 className="font-black text-white text-lg mb-6 leading-tight tracking-tighter group-hover:text-indigo-400 transition-colors">{card.name}</h4>
                              
                              <div className="flex items-center justify-between mt-auto">
                                 <div className="flex gap-2 flex-wrap">
                                    {card.tags.slice(0, 2).map((tag: string) => (
                                      <span key={tag} className="px-3 py-1 rounded-xl bg-white/5 text-gray-500 text-[9px] font-black uppercase tracking-widest group-hover:text-gray-300 transition-colors">
                                        {tag}
                                      </span>
                                    ))}
                                 </div>
                                 <div className="text-xl font-black text-white tracking-tighter flex items-center gap-2">
                                    <ShieldCheck size={16} className="text-emerald-500" /> {card.score}
                                 </div>
                              </div>
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                      
                      <button className="w-full py-6 rounded-[2rem] border-2 border-dashed border-white/5 text-[10px] text-gray-700 font-black uppercase tracking-[0.3em] hover:border-indigo-500/20 hover:text-indigo-400 hover:bg-indigo-500/5 transition-all flex items-center justify-center gap-4 group/add active:scale-95">
                        <Plus size={18} className="group-hover/add:scale-125 transition-transform" /> Register Entity
                      </button>
                    </div>
                  )}
                </Droppable>

              </div>
            ))}
          </div>
        </DragDropContext>
      </div>

      {/* Board Global Analytics Overlay */}
      <AnimatePresence>
          <motion.div 
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="fixed bottom-6 lg:bottom-10 left-4 right-4 lg:left-1/2 lg:-translate-x-1/2 flex flex-col sm:flex-row gap-4 sm:gap-6 px-6 sm:px-10 py-4 sm:py-5 rounded-[2rem] lg:rounded-[2.5rem] bg-black/60 border border-white/10 backdrop-blur-3xl shadow-[0_20px_60px_rgba(0,0,0,0.8)] z-50 items-center ring-1 ring-white/10"
          >
              <div className="flex items-center justify-between w-full sm:w-auto sm:gap-6">
                <div className="flex items-center gap-3 sm:gap-4">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                      <Clock size={16} className="text-indigo-400" />
                  </div>
                  <div>
                      <div className="text-[8px] sm:text-[9px] font-black text-gray-600 uppercase tracking-widest">Avg Speed</div>
                      <div className="text-[10px] sm:text-sm font-black text-emerald-400 mt-0.5 tracking-tight italic">14.2d</div>
                  </div>
                </div>
                
                <div className="sm:hidden w-px h-6 bg-white/10 mx-2" />
                
                <div className="flex items-center gap-3 sm:gap-4">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                      <Layers size={16} className="text-indigo-400" />
                  </div>
                  <div>
                      <div className="text-[8px] sm:text-[9px] font-black text-gray-600 uppercase tracking-widest">Volume</div>
                      <div className="text-[10px] sm:text-sm font-black text-white mt-0.5 tracking-tight italic">12 Units</div>
                  </div>
                </div>
              </div>

              <div className="hidden sm:block w-px h-8 bg-white/10 mx-2" />

              <button className="w-full sm:w-auto flex items-center justify-center gap-3 px-6 py-2.5 sm:py-3 rounded-[1.5rem] sm:rounded-2xl bg-white text-black font-black text-[10px] uppercase tracking-widest hover:bg-indigo-50 transition-all shadow-xl group/btn active:scale-95 sm:ml-4">
                 Analytics <ChevronRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
              </button>
          </motion.div>
      </AnimatePresence>
    </div>
  );
}


