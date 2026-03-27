"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Layers, Plus, MoreHorizontal, Activity, Target, Zap, Clock, ShieldCheck, ArrowRight, Radio, Filter, Sparkles, ChevronRight } from "lucide-react";
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd";
import { Target as TargetType } from "@/types";

interface Column {
  id: string;
  title: string;
  cards: any[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function PipelinePage() {
  const [columns, setColumns] = useState<Column[]>([]);
  const [isClient, setIsClient] = useState(false);
  const [loading, setLoading] = useState(true);
  const [processingAction, setProcessingAction] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const handleAction = (name: string, message: string) => {
    setProcessingAction(name);
    setTimeout(() => {
      setProcessingAction(null);
      setNotification(message);
    }, 1500);
  };

  useEffect(() => {
    setIsClient(true);
    setLoading(true);
    fetch(`/api/pipeline`)
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
      <AnimatePresence>
        {notification && (
          <motion.div 
            initial={{ opacity: 0, y: 50, x: '-50%' }}
            animate={{ opacity: 1, y: 0, x: '-50%' }}
            exit={{ opacity: 0, y: 20, x: '-50%' }}
            className="fixed bottom-10 left-1/2 z-[200] px-6 py-3 rounded-2xl bg-indigo-600 text-white font-black text-[10px] uppercase tracking-widest shadow-2xl flex items-center gap-3 border border-indigo-400 backdrop-blur-xl"
          >
            <ShieldCheck size={16} /> {notification}
          </motion.div>
        )}
      </AnimatePresence>

      <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 px-4 shrink-0">
        <div>
          <h1 className="text-3xl md:text-5xl font-black tracking-tighter text-white mb-3 flex flex-wrap items-center gap-4 sm:gap-5">
            EDRCF V5 Pipeline
            <div className="flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] text-emerald-400 font-black uppercase tracking-[0.2em]">
               <Radio size={14} className="animate-pulse" /> Radar Active
            </div>
          </h1>
          <p className="text-gray-400 text-base md:text-lg font-medium max-w-2xl leading-relaxed">
            Gestion du cycle d'origination. Les cibles sont classées par <span className="text-white">probabilité transactionnelle à 6-18 mois</span>.
          </p>
        </div>
        
        <div className="flex gap-4 items-center">
             <button 
               onClick={() => handleAction('sync', 'Full radar synchronization complete.')}
               className="px-8 py-3.5 rounded-2xl bg-indigo-600 text-white shadow-2xl shadow-indigo-600/30 hover:bg-indigo-500 transition-all flex items-center justify-center gap-3 font-black text-[11px] uppercase tracking-widest active:scale-95"
             >
               {processingAction === 'sync' ? (
                  <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
               ) : (
                  <Sparkles size={16} />
               )}
               Radar Sync
             </button>
        </div>
      </header>

      <div className="flex-1 overflow-x-auto pb-20 px-4 custom-scrollbar">
        <DragDropContext onDragEnd={onDragEnd}>
          <div className="flex gap-8 h-full min-w-max">
             {columns.map((column) => (
              <div key={column.id} className="w-[340px] flex flex-col h-full bg-black/40 rounded-[3rem] border border-white/10 shadow-2xl overflow-hidden backdrop-blur-3xl group/col shrink-0">
                
                <div className="p-8 pb-5 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-2 h-8 rounded-full ${
                      column.id === 'opp' ? 'bg-emerald-500' : 
                      column.id === 'prio' ? 'bg-indigo-500' : 
                      column.id === 'prep' ? 'bg-amber-500' :
                      'bg-gray-500'
                    }`} />
                    <h3 className="font-black text-white text-[11px] uppercase tracking-[0.3em]">{column.title}</h3>
                  </div>
                  <span className="px-4 py-1.5 rounded-2xl bg-white/5 border border-white/10 text-gray-400 text-[10px] font-black">{column.cards.length}</span>
                </div>

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
                              <div className="flex justify-between items-start mb-6">
                                <span className="px-2.5 py-1 rounded-xl text-[9px] font-black tracking-widest uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/10">
                                  {card.sector}
                                </span>
                                <div className="text-lg font-black text-white tracking-tighter italic">
                                   Score {card.score}
                                </div>
                              </div>
                              
                              <h4 className="font-black text-white text-lg mb-6 leading-tight tracking-tighter uppercase">{card.name}</h4>
                              
                              <div className="flex items-center justify-between">
                                 <div className="flex gap-2">
                                    {card.tags.map((tag: string) => (
                                      <span key={tag} className="px-3 py-1 rounded-xl bg-white/5 text-gray-400 text-[9px] font-black uppercase tracking-widest">
                                        {tag}
                                      </span>
                                    ))}
                                 </div>
                                 <button onClick={() => window.location.href=`/targets/${card.id}`} className="p-2 rounded-xl bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition-all">
                                    <ChevronRight size={18} />
                                 </button>
                              </div>
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                      
                      <button 
                        onClick={() => handleAction('register', 'Opening entity registration vault...')}
                        className="w-full py-6 rounded-[2rem] border-2 border-dashed border-white/5 text-[10px] text-gray-700 font-black uppercase tracking-[0.3em] hover:border-indigo-500/20 hover:text-indigo-400 transition-all flex items-center justify-center gap-4 group/add active:scale-95"
                      >
                        <Plus size={18} /> Register Entity
                      </button>
                    </div>
                  )}
                </Droppable>

              </div>
            ))}
          </div>
        </DragDropContext>
      </div>

      <motion.div 
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="fixed bottom-10 left-1/2 -translate-x-1/2 flex gap-12 px-10 py-5 rounded-[2.5rem] bg-black/60 border border-white/10 backdrop-blur-3xl shadow-2xl z-50 items-center ring-1 ring-white/10"
      >
        <div className="flex items-center gap-4">
          <Activity size={20} className="text-indigo-400" />
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Pipeline Health: <span className="text-emerald-400">Optimal</span></div>
        </div>
        <div className="h-4 w-px bg-white/10" />
        <div className="flex items-center gap-4">
          <Clock size={20} className="text-indigo-400" />
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Avg Time: <span className="text-white">12.4 Days</span></div>
        </div>
      </motion.div>
    </div>
  );
}
