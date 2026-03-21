import { useEffect, useRef } from "react";
import { useTheme } from "next-themes";
import ExcalidrawCanvas, { ExcalidrawCanvasRef } from "../components/ExcalidrawCanvas";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Home } from "lucide-react";
import { Button } from "../components/ui/button";

const Explore = () => {
  const { theme, systemTheme } = useTheme();
  const currentTheme = theme === "system" ? systemTheme : theme;
  const isDark = currentTheme === "dark";
  const excalidrawRef = useRef<ExcalidrawCanvasRef>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Auto-save to localStorage every 30 seconds
    const autoSaveInterval = setInterval(() => {
      if (excalidrawRef.current) {
        const elements = excalidrawRef.current.getSceneElements();
        const appState = excalidrawRef.current.getAppState();
        localStorage.setItem(
          "explore-excalidraw-data",
          JSON.stringify({ elements, appState })
        );
      }
    }, 30000);

    return () => clearInterval(autoSaveInterval);
  }, []);

  // Load saved data on mount
  useEffect(() => {
    const savedData = localStorage.getItem("explore-excalidraw-data");
    if (savedData && excalidrawRef.current) {
      try {
        const parsedData = JSON.parse(savedData);
        excalidrawRef.current.updateScene(parsedData);
      } catch (error) {
        console.error("Failed to load saved Excalidraw data:", error);
      }
    }
  }, [excalidrawRef.current]);

  return (
    <div className={`min-h-screen ${isDark ? 'bg-[#0a0a0a]' : 'bg-gray-50'}`}>
      {/* Excalidraw Canvas */}
      <div className="h-screen">
        <ExcalidrawCanvas ref={excalidrawRef} />
      </div>

      {/* Info Banner */}
      <div className={`fixed bottom-4 left-1/2 transform -translate-x-1/2 ${isDark ? 'bg-[#171717] border-[#2a2a2a]' : 'bg-white border-gray-200'} border rounded-lg px-4 py-2 shadow-lg`}>
        <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Your work is auto-saved every 30 seconds. No login required!
        </p>
      </div>
    </div>
  );
};

export default Explore;
