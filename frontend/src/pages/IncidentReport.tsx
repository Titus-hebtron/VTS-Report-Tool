import { useState } from 'react'
import { Upload } from 'lucide-react'

export function IncidentReport() {
  const [incidentType, setIncidentType] = useState('incident')
  const [formData, setFormData] = useState({
    patrolCar: '',
    incidentDate: '',
    incidentTime: '',
    caller: '',
    phoneNumber: '',
    location: '',
    bound: '',
    chainage: '',
    description: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Submitting incident report:', formData)
    // TODO: Implement API call
  }

  return (
    <div>
      <h1 className="heading-1 mb-6">Incident Report</h1>

      <div className="bg-surface rounded-lg shadow p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Incident Type</label>
              <select
                value={incidentType}
                onChange={(e) => setIncidentType(e.target.value)}
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="incident">Incident</option>
                <option value="accident">Accident</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Patrol Car</label>
              <select
                value={formData.patrolCar}
                onChange={(e) => setFormData({ ...formData, patrolCar: e.target.value })}
                required
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select Vehicle</option>
                <option value="KDG 320Z">KDG 320Z</option>
                <option value="KDS 374F">KDS 374F</option>
                <option value="KDK 825Y">KDK 825Y</option>
                <option value="KDC 873G">KDC 873G</option>
                <option value="KDD 500X">KDD 500X</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Incident Date</label>
              <input
                type="date"
                value={formData.incidentDate}
                onChange={(e) => setFormData({ ...formData, incidentDate: e.target.value })}
                required
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Incident Time</label>
              <input
                type="time"
                value={formData.incidentTime}
                onChange={(e) => setFormData({ ...formData, incidentTime: e.target.value })}
                required
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Caller Name</label>
              <input
                type="text"
                value={formData.caller}
                onChange={(e) => setFormData({ ...formData, caller: e.target.value })}
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Phone Number</label>
              <input
                type="tel"
                value={formData.phoneNumber}
                onChange={(e) => setFormData({ ...formData, phoneNumber: e.target.value })}
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Location</label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                required
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Bound</label>
              <select
                value={formData.bound}
                onChange={(e) => setFormData({ ...formData, bound: e.target.value })}
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select Bound</option>
                <option value="Nairobi Bound">Nairobi Bound</option>
                <option value="Mombasa Bound">Mombasa Bound</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Chainage</label>
              <input
                type="text"
                value={formData.chainage}
                onChange={(e) => setFormData({ ...formData, chainage: e.target.value })}
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={4}
              className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Upload Images</label>
            <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
              <Upload className="w-12 h-12 mx-auto mb-4 text-text-secondary" />
              <p className="text-text-secondary mb-2">Drag and drop images here, or click to browse</p>
              <input type="file" multiple accept="image/*" className="hidden" />
              <button
                type="button"
                className="px-4 py-2 bg-background text-primary font-medium rounded-lg hover:bg-border transition-colors"
              >
                Choose Files
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-4">
            <button
              type="button"
              className="px-6 py-2 border border-border rounded-lg hover:bg-background transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-primary text-white font-medium rounded-lg hover:bg-secondary transition-colors"
            >
              Submit Report
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}