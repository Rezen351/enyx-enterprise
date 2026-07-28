
/**
 * AeroponicSchematic - Complete reactive SVG component migrated from public/aeroponic-system.svg
 */
const AeroponicSchematic = ({ 
  isMistPumpOn = false, 
  isInletPumpOn = false, 
  isValveOn = false, 
  reservoirLevel = 0, 
  systemHealth = 'healthy',
  telemetry = {}
}) => {
  const safeTelemetry = telemetry || {};
  
  // Dynamic status color
  const getStatusColor = () => {
    if (systemHealth === 'degraded') return "#f59e0b";
    if (systemHealth === 'healthy') return "#10b981";
    return "#64748b";
  };

  return (
    <div className="relative w-full h-full flex items-center justify-center bg-slate-950/10 rounded-xl p-2 overflow-hidden">
      <style>
        {`
          @keyframes schematic-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes schematic-pulse {
            0%, 100% { opacity: 0.15; }
            50% { opacity: 0.45; }
          }
          .schematic-spin { animation: schematic-spin 1s linear infinite; }
          .schematic-pulse { animation: schematic-pulse 2s ease-in-out infinite; }
          .schematic-transition { transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
        `}
      </style>

      <svg
        width="100%"
        height="100%"
        viewBox="0 0 707 425"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="max-w-4xl"
      >
        {/* Background / Structure */}
        <rect id="rect819" x="192.263" y="180.263" width="475.49" height="199.137" fill="#0c111d" stroke="#1f2937" strokeWidth="0.526316" />
        <path id="path821" d="M195.365 0H178.826V379.359H195.365V0Z" fill="#1f2937" />
        <path id="path823" d="M435.177 12.4043H418.638V161.253H435.177V12.4043Z" fill="#1f2937" />
        <path id="path825" d="M658.451 12.4043H195.365V18.6063H658.451V12.4043Z" fill="#374151" />
        
        {/* Mist area glow */}
        <rect 
          x="195" y="19" width="463" height="161" 
          fill={isMistPumpOn ? "#00ffcc" : "transparent"} 
          className={isMistPumpOn ? "schematic-pulse" : ""}
          style={{ opacity: isMistPumpOn ? 0.3 : 0 }}
        />

        {/* Reservoir / Tank */}
        <g id="reservoir-section">
          <rect x="28.3" y="354" width="78.4" height="66.7" fill="#111827" stroke="#374151" />
          <rect 
            x="28.3" 
            y={354 + (66.7 * (1 - reservoirLevel / 100))} 
            width="78.4" 
            height={66.7 * (reservoirLevel / 100)} 
            fill={reservoirLevel < 20 ? "#ef4444" : "#3b82f6"} 
            className="schematic-transition"
            style={{ opacity: 0.6 }}
          />
          <text x="35" y="345" fill="#94a3b8" fontSize="10" fontWeight="bold">RES: {reservoirLevel}%</text>
        </g>

        {/* Inlet Pump */}
        <g id="inlet-pump-group">
          <circle cx="155.3" cy="405" r="12" fill="#1f2937" stroke="#374151" />
          <path
            className={isInletPumpOn ? "schematic-spin" : ""}
            style={{ transformOrigin: "155.3px 405px" }}
            d="m 153.07,397.3 -0.3,0.1 c -0.1,0.4 0.3,3.5 0.4,4.4 -1.1,-1.2 -2.5,-2.4 -4.4,-2.0 -0.4,0.1 -1.2,0.3 -1.5,0.7 0.4,0.6 2.7,2.3 3.5,3.1 -3.1,-0.5 -4.4,0.4 -5.5,3.2 2, -0.3 3.1, -0.4 5.1, -0.4 -1.2,0.7 -2.4,1.8 -2.4,3.4 0,0.8 0,1.6 0.6,2.3 0.8,-0.1 2.1,-2.2 3,-3.2 0,2.7 0.2,4 2.9,5.2 l 0.1,0 c 0.2,-0.4 -0.2,-3.6 -0.2,-4.4 1.9,2.1 3.7,2.6 6.2,1.2 -1.5,-1 -2.3,-1.6 -3.6,-2.9 2.9,0.1 4.3,-0.4 5.2,-3.4 -1.6,0.4 -3.1,0.4 -4.8,0.5 2,-1.3 2.6,-2.5 2.1,-5 -0.1,-0.4 -0.2,-0.7 -0.6,-1.0 -0.5,0.4 -1.8,2.4 -3,3.5 0.5,-2.7 -0.5,-4.1 -2.8,-5.3 z"
            fill={isInletPumpOn ? "#00ffcc" : "#4b5563"}
          />
        </g>

        {/* Mist Pump (Top) */}
        <g id="mist-pump-group" transform="translate(0, -220)">
           <circle cx="155.3" cy="405" r="12" fill="#1f2937" stroke="#374151" />
           <path
            className={isMistPumpOn ? "schematic-spin" : ""}
            style={{ transformOrigin: "155.3px 405px" }}
            d="m 153.07,397.3 -0.3,0.1 c -0.1,0.4 0.3,3.5 0.4,4.4 -1.1,-1.2 -2.5,-2.4 -4.4,-2.0 -0.4,0.1 -1.2,0.3 -1.5,0.7 0.4,0.6 2.7,2.3 3.5,3.1 -3.1,-0.5 -4.4,0.4 -5.5,3.2 2, -0.3 3.1, -0.4 5.1, -0.4 -1.2,0.7 -2.4,1.8 -2.4,3.4 0,0.8 0,1.6 0.6,2.3 0.8,-0.1 2.1,-2.2 3,-3.2 0,2.7 0.2,4 2.9,5.2 l 0.1,0 c 0.2,-0.4 -0.2,-3.6 -0.2,-4.4 1.9,2.1 3.7,2.6 6.2,1.2 -1.5,-1 -2.3,-1.6 -3.6,-2.9 2.9,0.1 4.3,-0.4 5.2,-3.4 -1.6,0.4 -3.1,0.4 -4.8,0.5 2,-1.3 2.6,-2.5 2.1,-5 -0.1,-0.4 -0.2,-0.7 -0.6,-1.0 -0.5,0.4 -1.8,2.4 -3,3.5 0.5,-2.7 -0.5,-4.1 -2.8,-5.3 z"
            fill={isMistPumpOn ? "#00ffcc" : "#4b5563"}
          />
        </g>

        {/* Valve */}
        <rect x="330" y="12" width="20" height="12" fill={isValveOn ? "#00ffcc" : "#4b5563"} stroke="#374151" />

        {/* Monitor Screen */}
        <g id="monitor">
          <rect x="383.08" y="102.264" width="87.4246" height="55.9011" rx="4.23729" fill="#0c111d" stroke="#1f2937" strokeWidth="0.526316" />
          <text x="427" y="135" textAnchor="middle" fill={getStatusColor()} fontSize="11" fontWeight="black" className="schematic-pulse">
            {systemHealth.toUpperCase()}
          </text>
        </g>

        {/* Data Overlays */}
        <g fontSize="11" fontWeight="bold">
          <text x="50" y="70" fill="#fbbf24">TEMP: {safeTelemetry?.cwt_dalam_temp?.value ?? '--'}°C</text>
          <text x="50" y="85" fill="#38bdf8">HUM: {safeTelemetry?.cwt_dalam_hum?.value ?? '--'}%</text>
          <text x="50" y="140" fill="#a78bfa">PH: {safeTelemetry?.npk_ph?.value ?? '--'}</text>
          <text x="50" y="155" fill="#4ade80">EC: {safeTelemetry?.npk_ec?.value ?? '--'} mS</text>
          <text x="50" y="170" fill="#fbbf24">TEMP: {safeTelemetry?.npk_temp_air?.value ?? '--'}°C</text>
        </g>

        {/* Lasers / Indicators */}
        <rect x="192" y="280" width="27" height="20" fill="#1f2937" />
        <circle cx="215" cy="290" r="3" fill={systemHealth === 'healthy' ? "#10b981" : "#ef4444"} />
        {systemHealth === 'healthy' && (
          <line x1="217" y1="290" x2="426" y2="290" stroke="#ef4444" strokeWidth="0.5" strokeDasharray="2 2" className="schematic-pulse" />
        )}
      </svg>
    </div>
  );
};

export default AeroponicSchematic;
