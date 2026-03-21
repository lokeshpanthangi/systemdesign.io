import { Home, List, TrendingUp, Settings, LogOut, ChevronLeft, ChevronRight, Compass } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useSidebar } from "@/contexts/SidebarContext";
import { authService } from "@/services/authService";
import { useEffect, useState } from "react";
import type { User } from "@/types/api";
import { Logo } from "@/components/Logo";

export const AppSidebar = () => {
  const navigate = useNavigate();
  const { isCollapsed, toggleSidebar } = useSidebar();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Load user from localStorage or fetch from API
    const storedUser = authService.getStoredUser();
    if (storedUser) {
      setUser(storedUser);
    } else {
      // Fetch current user
      authService.getCurrentUser()
        .then(setUser)
        .catch(console.error);
    }
  }, []);

  const navItems = [
    { title: "Dashboard", url: "/dashboard", icon: Home },
    { title: "Explore", url: "/explore", icon: Compass },
    { title: "All Questions", url: "/questions", icon: List },
    { title: "My Progress", url: "/progress", icon: TrendingUp },
    { title: "Settings", url: "/settings", icon: Settings },
  ];

  const handleLogout = () => {
    authService.logout();
    navigate("/");
  };

  return (
    <aside className={cn(
      "fixed left-0 top-0 h-screen bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300 ease-in-out z-50",
      isCollapsed ? "w-16" : "w-64"
    )}>
      {/* Logo */}
      <div className={cn(
        "border-b border-sidebar-border flex items-center justify-between",
        isCollapsed ? "p-4" : "p-6"
      )}>
        {isCollapsed ? (
          <Logo size={28} className="text-primary" />
        ) : (
          <div className="flex items-center gap-3">
            <Logo size={32} className="text-primary" />
            <div>
              <h1 className="text-xl font-bold text-primary">SystemDesign.io</h1>
              <p className="text-xs text-muted-foreground mt-1">Master system design</p>
            </div>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-sidebar-accent transition-colors"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 text-sidebar-foreground" />
          ) : (
            <ChevronLeft className="w-4 h-4 text-sidebar-foreground" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.url}
            to={item.url}
            end={item.url === "/dashboard"}
            className={({ isActive }) =>
              cn(
                "flex items-center rounded-lg text-sm font-medium transition-smooth",
                isCollapsed ? "justify-center p-3" : "gap-3 px-4 py-3",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50"
              )
            }
            title={isCollapsed ? item.title : undefined}
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span>{item.title}</span>}
          </NavLink>
        ))}
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-sidebar-border">
        {user && (
          <div className={cn(
            "flex items-center rounded-lg bg-sidebar-accent",
            isCollapsed ? "justify-center p-2" : "gap-3 p-3"
          )}>
            <div className="w-10 h-10 rounded-full bg-orange-500 flex items-center justify-center flex-shrink-0 text-white font-semibold">
              {user.first_name[0]}{user.last_name[0]}
            </div>
            {!isCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-sidebar-foreground truncate">
                  {user.first_name} {user.last_name}
                </p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
            )}
          </div>
        )}
        
        {/* Theme Toggle */}
        {!isCollapsed && (
          <div className="mt-2">
            <ThemeToggle />
          </div>
        )}
        
        <button
          onClick={handleLogout}
          className={cn(
            "w-full flex items-center text-sm text-muted-foreground hover:text-foreground transition-smooth mt-2",
            isCollapsed ? "justify-center p-2" : "gap-2 px-4 py-2"
          )}
          title={isCollapsed ? "Logout" : undefined}
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
};
