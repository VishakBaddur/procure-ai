import React from 'react'
import { Link, useParams } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { 
  LayoutDashboard, 
  FileText, 
  FileCheck, 
  Star, 
  TrendingUp,
  ArrowLeft,
  Lightbulb,
  Calculator
} from 'lucide-react'
import { cn } from '@/lib/utils'

const ProjectLayout = ({ children, activePath }) => {
  const { projectId } = useParams()
  const [project, setProject] = React.useState(null)

  React.useEffect(() => {
    if (projectId) {
      axios.get(`${API_BASE}/api/projects/${projectId}`)
        .then(res => setProject(res.data.project))
        .catch(() => {})
    }
  }, [projectId])

  const navItems = [
    { path: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: 'quotations', label: 'Quotations', icon: FileText },
    { path: 'agreements', label: 'Agreements', icon: FileCheck },
    { path: 'reviews', label: 'Reviews', icon: Star },
    { path: 'tco', label: 'TCO', icon: TrendingUp },
    { path: 'decision', label: 'Decision Assistance', icon: Lightbulb },
    { path: 'what-if', label: 'What-If Analysis', icon: Calculator },
  ]

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <div className="w-64 border-r bg-background">
        <div className="p-6 border-b">
          <Link to="/projects" className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Projects
          </Link>
          {project && (
            <>
              <h2 className="font-semibold text-lg">{project.name}</h2>
              <p className="text-sm text-muted-foreground mt-1">{project.item_name}</p>
            </>
          )}
        </div>
        
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = activePath === item.path
            return (
              <Link
                key={item.path}
                to={`/projects/${projectId}/${item.path}`}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  active
                    ? "bg-foreground text-background font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  )
}

export default ProjectLayout
