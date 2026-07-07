import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ZoomIn, ZoomOut, X, FileText, Calendar, Activity, ShieldAlert, Hash } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import { getAdminGraph } from '../../lib/api';
import PageTransition from '../../components/PageTransition';

export default function GraphView() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  
  // Interactive states
  const [hoveredNode, setHoveredNode] = useState<any>(null);
  const [pinnedNode, setPinnedNode] = useState<any>(null);
  
  const fgRef = useRef<any>(null);

  useEffect(() => {
    getAdminGraph().then(data => {
      setGraphData({ nodes: data.nodes, links: data.edges } as any);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  // Update forces when graph loads
  useEffect(() => {
    if (fgRef.current && !loading) {
      // D3 clustering: charge pulls nodes together, center force keeps them central
      fgRef.current.d3Force('charge').strength(-300);
      fgRef.current.d3Force('link').distance(40);
    }
  }, [loading, graphData]);

  // Derived stats for top bar
  const stats = useMemo(() => {
    if (!graphData.nodes.length) return null;
    const sessions = graphData.nodes.filter((n: any) => n.group === 'session');
    const entities = graphData.nodes.filter((n: any) => n.group === 'entity');
    
    let maxCluster = 0;
    entities.forEach((e: any) => { if (e.report_count > maxCluster) maxCluster = e.report_count; });
    
    const today = new Date();
    today.setHours(0,0,0,0);
    const flaggedToday = sessions.filter((s: any) => new Date(s.created_at) >= today).length;
    
    return {
      totalSessions: sessions.length,
      totalEntities: entities.length,
      largestCluster: maxCluster,
      flaggedToday
    };
  }, [graphData]);

  const handleNodeHover = useCallback((node: any) => {
    if (!pinnedNode) {
      setHoveredNode(node);
    }
  }, [pinnedNode]);

  const handleNodeClick = useCallback((node: any) => {
    setPinnedNode(node);
    setHoveredNode(null);
    // Center/zoom on node
    fgRef.current.centerAt(node.x, node.y, 1000);
    fgRef.current.zoom(8, 2000);
  }, [fgRef]);

  const handleZoomIn = () => {
    if (fgRef.current) fgRef.current.zoom(fgRef.current.zoom() * 1.5, 400);
  };
  
  const handleZoomOut = () => {
    if (fgRef.current) fgRef.current.zoom(fgRef.current.zoom() / 1.5, 400);
  };

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const isEntity = node.group === 'entity';
    const size = node.val || 5;
    
    const isHovered = (hoveredNode && hoveredNode.id === node.id);
    const isPinned = (pinnedNode && pinnedNode.id === node.id);
    const isActive = isHovered || isPinned;
    
    // Draw node circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
    
    if (isEntity) {
      ctx.fillStyle = isActive ? '#d8b4fe' : '#a855f7'; // Purple
      ctx.fill();
      ctx.strokeStyle = isActive ? '#ffffff' : '#e9d5ff';
      ctx.lineWidth = isActive ? 2 / globalScale : 1 / globalScale;
      ctx.stroke();
    } else {
      ctx.fillStyle = node.risk_score >= 70 ? '#ef4444' : node.risk_score >= 40 ? '#eab308' : '#10b981';
      if (isActive) {
        ctx.fillStyle = node.risk_score >= 70 ? '#fca5a5' : node.risk_score >= 40 ? '#fde047' : '#6ee7b7';
      }
      ctx.fill();
      ctx.strokeStyle = isActive ? '#ffffff' : '#f8fafc';
      ctx.lineWidth = isActive ? 2 / globalScale : 1 / globalScale;
      ctx.stroke();
    }
    
    // Only draw label if node is active, to avoid collision clutter
    if (isActive && globalScale > 1) {
      const label = node.label;
      const fontSize = 14 / globalScale;
      ctx.font = `bold ${fontSize}px Sans-Serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // Draw label background
      const textWidth = ctx.measureText(label).width;
      const bgWidth = textWidth + (8 / globalScale);
      const bgHeight = fontSize + (6 / globalScale);
      
      ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
      ctx.fillRect(node.x - bgWidth/2, node.y + size + (4 / globalScale), bgWidth, bgHeight);
      
      // Draw text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, node.x, node.y + size + (4 / globalScale) + bgHeight/2);
    }
  }, [hoveredNode, pinnedNode]);

  const activeNode = pinnedNode || hoveredNode;

  return (
    <PageTransition>
      <div className="absolute inset-0 pt-16 z-0 bg-navy-900 flex flex-col overflow-hidden">
        
        {/* Top Stats Bar */}
        <div className="w-full bg-navy-900/90 border-b border-white/10 p-4 flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-slate-400 hover:text-white flex items-center gap-2 text-sm transition-colors border-r border-white/10 pr-4">
              <ArrowLeft className="w-4 h-4" /> Back
            </Link>
            <h2 className="font-bold text-lg hidden md:block">Fraud Network Graph</h2>
          </div>
          
          {stats && (
            <div className="flex gap-4 lg:gap-8 overflow-x-auto no-scrollbar">
              <div className="flex flex-col">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Total Reports</span>
                <span className="font-bold text-lg text-white flex items-center gap-1"><FileText className="w-4 h-4 text-electric-blue"/> {stats.totalSessions}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Tracked Entities</span>
                <span className="font-bold text-lg text-white flex items-center gap-1"><Hash className="w-4 h-4 text-purple-400"/> {stats.totalEntities}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Largest Cluster</span>
                <span className="font-bold text-lg text-white flex items-center gap-1"><Activity className="w-4 h-4 text-alert-red"/> {stats.largestCluster} nodes</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Flagged Today</span>
                <span className="font-bold text-lg text-white flex items-center gap-1"><ShieldAlert className="w-4 h-4 text-yellow-500"/> {stats.flaggedToday}</span>
              </div>
            </div>
          )}
        </div>

        {/* Main Workspace */}
        <div className="flex-1 flex w-full relative overflow-hidden">
          
          {/* Left Canvas (65%) */}
          <div className="w-full lg:w-[65%] h-full relative cursor-crosshair">
            {/* Background Pattern */}
            <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)', backgroundSize: '24px 24px' }}></div>
            
            {loading ? (
              <div className="absolute inset-0 flex items-center justify-center text-slate-500">
                Loading graph data...
              </div>
            ) : (
              <ForceGraph2D
                ref={fgRef}
                graphData={graphData}
                nodeLabel="" // Disabled default tooltip in favor of our panel/custom draw
                nodeCanvasObject={paintNode}
                linkColor={() => 'rgba(255,255,255,0.15)'}
                linkWidth={1.5}
                onNodeHover={handleNodeHover}
                onNodeClick={handleNodeClick}
                onBackgroundClick={() => setPinnedNode(null)}
                enableZoomInteraction={false} // Disabled scroll zoom per requirements
                backgroundColor="transparent"
                cooldownTicks={100}
                d3AlphaDecay={0.02}
                d3VelocityDecay={0.3}
              />
            )}

            {/* Fixed Legend */}
            <div className="absolute bottom-6 left-6 glass p-4 rounded-xl border border-white/10 shadow-lg pointer-events-none">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Legend</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-purple-500"></span> Entity (Phone/Bank/UPI)</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-alert-red"></span> High Risk Report (70+)</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-yellow-500"></span> Medium Risk (40-69)</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-safe-green"></span> Low Risk (&lt;40)</div>
              </div>
            </div>

            {/* Zoom Controls */}
            <div className="absolute bottom-6 right-6 flex flex-col gap-2">
              <button onClick={handleZoomIn} className="w-10 h-10 rounded-xl glass border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors">
                <ZoomIn className="w-5 h-5 text-white" />
              </button>
              <button onClick={handleZoomOut} className="w-10 h-10 rounded-xl glass border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors">
                <ZoomOut className="w-5 h-5 text-white" />
              </button>
            </div>
          </div>

          {/* Right Detail Panel (35%) */}
          <div className="hidden lg:flex w-[35%] bg-navy-800/95 border-l border-white/10 h-full flex-col z-20 overflow-y-auto backdrop-blur-xl">
            {!activeNode ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 p-8 text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
                  <Activity className="w-8 h-8 opacity-50" />
                </div>
                <p>Hover over or click a node on the graph to view its detailed intelligence profile here.</p>
              </div>
            ) : (
              <div className="p-6 relative animate-in fade-in slide-in-from-right-4 duration-300">
                {pinnedNode && (
                  <button 
                    onClick={() => setPinnedNode(null)} 
                    className="absolute top-6 right-6 p-1.5 rounded-lg bg-white/5 hover:bg-alert-red/20 hover:text-alert-red transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}
                
                {activeNode.group === 'session' ? (
                  // SESSION NODE PANEL
                  <>
                    <div className="flex items-center gap-3 mb-6">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${activeNode.risk_score >= 70 ? 'bg-alert-red/20 text-alert-red' : activeNode.risk_score >= 40 ? 'bg-yellow-500/20 text-yellow-500' : 'bg-safe-green/20 text-safe-green'}`}>
                        <ShieldAlert className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-white">Fraud Report</h3>
                        <p className="text-slate-400 font-mono text-xs font-bold">REP-{activeNode.id.split('-')[0].toUpperCase()}</p>
                      </div>
                    </div>

                    <div className="space-y-6">
                      <div className="bg-navy-900 p-4 rounded-xl border border-white/5">
                        <p className="text-sm text-slate-400 mb-1 uppercase tracking-wider font-bold">AI Risk Verdict</p>
                        <p className={`text-3xl font-black ${activeNode.risk_score >= 70 ? 'text-alert-red' : activeNode.risk_score >= 40 ? 'text-yellow-500' : 'text-safe-green'}`}>
                          {activeNode.risk_score}/100
                        </p>
                      </div>
                      
                      <div>
                        <p className="text-sm text-slate-400 mb-2 flex items-center gap-2"><Calendar className="w-4 h-4"/> Reported On</p>
                        <p className="text-slate-200">{new Date(activeNode.created_at).toLocaleString()}</p>
                      </div>

                      <div className="border-t border-white/10 pt-4">
                        <p className="text-sm text-slate-400 mb-2 font-bold">AI Explanation</p>
                        <p className="text-sm text-slate-300 leading-relaxed bg-navy-900/50 p-4 rounded-lg border border-white/5">
                          {activeNode.ai_explanation}
                        </p>
                      </div>

                      <div className="border-t border-white/10 pt-4">
                        <p className="text-sm text-slate-400 mb-2 font-bold">Original Transcript Snippet</p>
                        <p className="text-sm text-slate-300 leading-relaxed italic border-l-2 border-electric-blue pl-4 py-1">
                          "{activeNode.transcript_snippet}"
                        </p>
                      </div>
                    </div>
                  </>
                ) : (
                  // ENTITY NODE PANEL
                  <>
                    <div className="flex items-center gap-3 mb-6 pr-8">
                      <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-purple-500/20 text-purple-400 shrink-0">
                        <Hash className="w-6 h-6" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-xl font-bold text-white truncate" title={activeNode.entity_value}>{activeNode.entity_value}</h3>
                        <p className="text-sm text-slate-400 uppercase tracking-widest">{activeNode.entity_type.replace('_', ' ')}</p>
                      </div>
                    </div>

                    <div className="space-y-6">
                      <div className="bg-navy-900 p-4 rounded-xl border border-alert-red/20 shadow-[0_0_15px_rgba(239,68,68,0.1)]">
                        <p className="text-sm text-slate-400 mb-1 uppercase tracking-wider font-bold">Linked Fraud Reports</p>
                        <p className="text-3xl font-black text-alert-red flex items-center gap-2">
                          <Activity className="w-6 h-6" />
                          {activeNode.report_count}
                        </p>
                        <p className="text-xs text-slate-500 mt-2">This entity is the center of an organized cluster.</p>
                      </div>
                      
                      <div>
                        <p className="text-sm text-slate-400 mb-2 flex items-center gap-2"><Calendar className="w-4 h-4"/> First Seen in Network</p>
                        <p className="text-slate-200">{new Date(activeNode.first_seen).toLocaleString()}</p>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
