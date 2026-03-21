import { useState, useEffect, useCallback, forwardRef, useImperativeHandle } from "react";
import { Excalidraw, MainMenu, WelcomeScreen } from "@excalidraw/excalidraw";
import { useTheme } from "next-themes";

type ExcalidrawElement = any;
type AppState = any;
type ExcalidrawImperativeAPI = any;

interface ExcalidrawCanvasProps {
  onSceneUpdate?: (elements: ExcalidrawElement[], appState: AppState) => void;
  initialData?: {
    elements: ExcalidrawElement[];
    appState: Partial<AppState>;
  };
}

export interface ExcalidrawCanvasRef {
  getSceneElements: () => ExcalidrawElement[];
  getAppState: () => AppState;
  updateScene: (sceneData: { elements: ExcalidrawElement[]; appState: Partial<AppState> }) => void;
  resetScene: () => void;
  exportToBlob: (options: { mimeType: string }) => Promise<Blob>;
  addSystemDiagramElements: () => void;
  addFlowchartElements: () => void;
}

const ExcalidrawCanvas = forwardRef<ExcalidrawCanvasRef, ExcalidrawCanvasProps>(
  ({ onSceneUpdate, initialData }, ref) => {
    const { theme, systemTheme } = useTheme();
    const [excalidrawAPI, setExcalidrawAPI] = useState<ExcalidrawImperativeAPI | null>(null);

    // Determine the current theme
    const currentTheme = theme === "system" ? systemTheme : theme;
    const excalidrawTheme = currentTheme === "dark" ? "dark" : "light";

    // Helper function to ensure proper app state structure
    const ensureValidAppState = (appState: Partial<AppState>): Partial<AppState> => {
      return {
        ...appState,
        collaborators: appState.collaborators || new Map(),
      };
    };

    useImperativeHandle(ref, () => ({
      getSceneElements: () => excalidrawAPI?.getSceneElements() || [],
      getAppState: () => excalidrawAPI?.getAppState() || ({} as AppState),
      updateScene: (sceneData) => {
        if (excalidrawAPI) {
          const safeSceneData = {
            ...sceneData,
            appState: sceneData.appState ? ensureValidAppState(sceneData.appState) : undefined,
          };
          excalidrawAPI.updateScene(safeSceneData);
        }
      },
      resetScene: () => {
        if (excalidrawAPI) {
          excalidrawAPI.resetScene();
        }
      },
      exportToBlob: (options) => {
        if (excalidrawAPI) {
          return excalidrawAPI.exportToBlob(options);
        }
        return Promise.reject(new Error("Excalidraw API not available"));
      },
      addSystemDiagramElements: () => addSystemDiagramTemplate(),
      addFlowchartElements: () => addFlowchartTemplate(),
    }));

    const handleChange = useCallback(
      (elements: ExcalidrawElement[], appState: AppState) => {
        onSceneUpdate?.(elements, appState);
      },
      [onSceneUpdate]
    );

    // Template functions for common system design patterns
    const addSystemDiagramTemplate = () => {
      if (!excalidrawAPI) return;

      const elements: ExcalidrawElement[] = [
        // Load Balancer
        {
          id: "load-balancer",
          type: "rectangle",
          x: 100,
          y: 100,
          width: 120,
          height: 60,
          angle: 0,
          strokeColor: "#1e1e1e",
          backgroundColor: "#e7f3ff",
          fillStyle: "solid",
          strokeWidth: 2,
          strokeStyle: "solid",
          roughness: 1,
          opacity: 100,
          groupIds: [],
          frameId: null,
          roundness: { type: 3 },
          seed: Math.floor(Math.random() * 100000),
          versionNonce: Math.floor(Math.random() * 100000),
          isDeleted: false,
          boundElements: null,
          updated: 1,
          link: null,
          locked: false,
        },
        // Application Servers
        {
          id: "app-server-1",
          type: "rectangle",
          x: 50,
          y: 250,
          width: 100,
          height: 60,
          angle: 0,
          strokeColor: "#1e1e1e",
          backgroundColor: "#fff2cc",
          fillStyle: "solid",
          strokeWidth: 2,
          strokeStyle: "solid",
          roughness: 1,
          opacity: 100,
          groupIds: [],
          frameId: null,
          roundness: { type: 3 },
          seed: Math.floor(Math.random() * 100000),
          versionNonce: Math.floor(Math.random() * 100000),
          isDeleted: false,
          boundElements: null,
          updated: 1,
          link: null,
          locked: false,
        },
        {
          id: "app-server-2",
          type: "rectangle",
          x: 170,
          y: 250,
          width: 100,
          height: 60,
          angle: 0,
          strokeColor: "#1e1e1e",
          backgroundColor: "#fff2cc",
          fillStyle: "solid",
          strokeWidth: 2,
          strokeStyle: "solid",
          roughness: 1,
          opacity: 100,
          groupIds: [],
          frameId: null,
          roundness: { type: 3 },
          seed: Math.floor(Math.random() * 100000),
          versionNonce: Math.floor(Math.random() * 100000),
          isDeleted: false,
          boundElements: null,
          updated: 1,
          link: null,
          locked: false,
        },
        // Database
        {
          id: "database",
          type: "ellipse",
          x: 110,
          y: 400,
          width: 100,
          height: 60,
          angle: 0,
          strokeColor: "#1e1e1e",
          backgroundColor: "#f8cecc",
          fillStyle: "solid",
          strokeWidth: 2,
          strokeStyle: "solid",
          roughness: 1,
          opacity: 100,
          groupIds: [],
          frameId: null,
          roundness: null,
          seed: Math.floor(Math.random() * 100000),
          versionNonce: Math.floor(Math.random() * 100000),
          isDeleted: false,
          boundElements: null,
          updated: 1,
          link: null,
          locked: false,
        },
        // Arrows
        {
          id: "arrow-1",
          type: "arrow",
          x: 160,
          y: 160,
          width: 0,
          height: 80,
          angle: 0,
          strokeColor: "#1e1e1e",
          backgroundColor: "transparent",
          fillStyle: "solid",
          strokeWidth: 2,
          strokeStyle: "solid",
          roughness: 1,
          opacity: 100,
          groupIds: [],
          frameId: null,
          roundness: { type: 2 },
          seed: Math.floor(Math.random() * 100000),
          versionNonce: Math.floor(Math.random() * 100000),
          isDeleted: false,
          boundElements: null,
          updated: 1,
          link: null,
          locked: false,
          startBinding: null,
          endBinding: null,
          lastCommittedPoint: null,
          startArrowhead: null,
          endArrowhead: "arrow",
          points: [[0, 0], [0, 80]],
        },
      ];

      excalidrawAPI.updateScene({
        elements: [...excalidrawAPI.getSceneElements(), ...elements],
      });
    };

    const addFlowchartTemplate = () => {
      if (!excalidrawAPI) return;

      const elements: ExcalidrawElement[] = [
        // Start
        {
          id: "start",
          type: "ellipse",
          x: 200,
          y: 50,
          width: 100,
          height: 50,
          angle: 0,
          strokeColor: "#1e1e1e",
          backgroundColor: "#d5e8d4",
          fillStyle: "solid",
          strokeWidth: 2,
          strokeStyle: "solid",
          roughness: 1,
          opacity: 100,
          groupIds: [],
          frameId: null,
          roundness: null,
          seed: Math.floor(Math.random() * 100000),
          versionNonce: Math.floor(Math.random() * 100000),
          isDeleted: false,
          boundElements: null,
          updated: 1,
          link: null,
          locked: false,
        },
        // Process
        {
          id: "process",
          type: "rectangle",
          x: 175,
          y: 150,
          width: 150,
          height: 60,
          angle: 0,
          strokeColor: "#1e1e1e",
          backgroundColor: "#e1d5e7",
          fillStyle: "solid",
          strokeWidth: 2,
          strokeStyle: "solid",
          roughness: 1,
          opacity: 100,
          groupIds: [],
          frameId: null,
          roundness: { type: 3 },
          seed: Math.floor(Math.random() * 100000),
          versionNonce: Math.floor(Math.random() * 100000),
          isDeleted: false,
          boundElements: null,
          updated: 1,
          link: null,
          locked: false,
        },
        // Decision
        {
          id: "decision",
          type: "diamond",
          x: 200,
          y: 250,
          width: 100,
          height: 80,
          angle: 0,
          strokeColor: "#1e1e1e",
          backgroundColor: "#fff2cc",
          fillStyle: "solid",
          strokeWidth: 2,
          strokeStyle: "solid",
          roughness: 1,
          opacity: 100,
          groupIds: [],
          frameId: null,
          roundness: null,
          seed: Math.floor(Math.random() * 100000),
          versionNonce: Math.floor(Math.random() * 100000),
          isDeleted: false,
          boundElements: null,
          updated: 1,
          link: null,
          locked: false,
        },
      ];

      excalidrawAPI.updateScene({
        elements: [...excalidrawAPI.getSceneElements(), ...elements],
      });
    };

    // Load initial data when API is ready
    useEffect(() => {
      if (excalidrawAPI && initialData) {
        const safeInitialData = {
          ...initialData,
          appState: initialData.appState ? ensureValidAppState(initialData.appState) : { collaborators: new Map() },
        };
        excalidrawAPI.updateScene(safeInitialData);
      }
    }, [excalidrawAPI, initialData]);

    return (
      <div className="w-full h-full">
        <Excalidraw
          excalidrawAPI={(api) => setExcalidrawAPI(api)}
          theme={excalidrawTheme}
          onChange={handleChange}
          initialData={{
            elements: [],
            appState: { collaborators: new Map() },
          }}
          UIOptions={{
            canvasActions: {
              loadScene: false,
              saveToActiveFile: false,
              export: false,
              toggleTheme: false,
            },
          }}
        >
          <MainMenu>
            <MainMenu.DefaultItems.ClearCanvas />
            <MainMenu.DefaultItems.SaveAsImage />
            <MainMenu.DefaultItems.ChangeCanvasBackground />
          </MainMenu>
          <WelcomeScreen>
            <WelcomeScreen.Hints.MenuHint />
            <WelcomeScreen.Hints.ToolbarHint />
          </WelcomeScreen>
        </Excalidraw>
      </div>
    );
  }
);

ExcalidrawCanvas.displayName = "ExcalidrawCanvas";

export default ExcalidrawCanvas;