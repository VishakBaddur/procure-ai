import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Plus, Trash2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'

const ProjectList = () => {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [projectToDelete, setProjectToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [])

  const fetchProjects = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/projects`)
      setProjects(response.data.projects || [])
      setError('')
    } catch (err) {
      setError('Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteClick = (e, project) => {
    e.preventDefault()
    e.stopPropagation()
    setProjectToDelete(project)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!projectToDelete) return
    
    setDeleting(true)
    try {
      await axios.delete(`${API_BASE}/api/projects/${projectToDelete.id}`)
      setDeleteDialogOpen(false)
      setProjectToDelete(null)
      // Refresh the project list
      await fetchProjects()
    } catch (err) {
      setError('Failed to delete project')
      setDeleteDialogOpen(false)
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Loading projects...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-12 max-w-6xl">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold tracking-tight mb-2">Projects</h1>
            <p className="text-muted-foreground">Manage your procurement projects</p>
          </div>
          <Link to="/projects/create">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Project
            </Button>
          </Link>
        </div>

        {error && (
          <div className="mb-6 p-4 border border-destructive bg-destructive/10 text-destructive rounded-md">
            {error}
          </div>
        )}

        {projects.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>No Projects</CardTitle>
              <CardDescription>Create your first procurement project to get started.</CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/projects/create">
                <Button>Create Project</Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map(project => (
              <Card key={project.id} className="hover:border-foreground/50 transition-colors h-full flex flex-col">
                <Link to={`/projects/${project.id}/dashboard`} className="flex-1">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-xl">{project.name}</CardTitle>
                        <CardDescription>{project.item_name}</CardDescription>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => handleDeleteClick(e, project)}
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {project.item_description && (
                      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                        {project.item_description}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {project.primary_focus.map((focus, idx) => (
                        <span
                          key={idx}
                          className="text-xs px-2 py-1 bg-muted rounded-md border"
                        >
                          {focus}
                        </span>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Created {new Date(project.created_at).toLocaleDateString()}
                    </p>
                  </CardContent>
                </Link>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Project</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{projectToDelete?.name}"? This action cannot be undone and will delete all associated vendors, documents, and data.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false)
                setProjectToDelete(null)
              }}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default ProjectList
