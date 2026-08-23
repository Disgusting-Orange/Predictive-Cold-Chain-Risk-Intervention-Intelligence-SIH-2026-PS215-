/**
 * Signal Chamber design system: route-level shell for the dark, precise, teal-accent Cold Chain AI experience.
 */
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import AdminDashboard from "./pages/AdminDashboard";
import ClientWorkspace from "./pages/ClientWorkspace";
import FieldAgent from "./pages/FieldAgent";
import FieldWorkspace from "./pages/FieldWorkspace";
import Home from "./pages/Home";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import PublicTracker from "./pages/PublicTracker";
import RoleDashboard from "./pages/RoleDashboard";
import ShipmentDetail from "./pages/ShipmentDetail";
import Signup from "./pages/Signup";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/signup" component={Signup} />
      <Route path="/login" component={Login} />
      <Route path="/field-agent" component={FieldWorkspace} />
      <Route path="/field-agent/mobile" component={FieldAgent} />
      <Route path="/client" component={ClientWorkspace} />
      <Route path="/track/:token" component={PublicTracker} />
      <Route path="/shipment/:id" component={ShipmentDetail} />
      <Route path="/dashboard/admin" component={AdminDashboard} />
      <Route path="/dashboard/:role" component={RoleDashboard} />
      <Route path="/404" component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="dark">
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
