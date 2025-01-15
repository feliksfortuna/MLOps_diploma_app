"use client"

import React, { useState } from 'react'
import Image from 'next/image'
import { ChevronDown } from 'lucide-react'
import axios from 'axios'

const races = [
  { id: 'tour-de-france', name: 'Tour de France', index: 0 },
  { id: 'giro-italia', name: 'Giro d\'Italia', index: 1 },
  { id: 'vuelta-espana', name: 'Vuelta a España', index: 2 },
  { id: 'paris-roubaix', name: 'Paris-Roubaix', index: 3 },
]

export default function CyclingRacePredictor() {
  const [selectedRace, setSelectedRace] = useState<{ id: string, name: string, index: number } | undefined>()
  const [topCyclists, setTopCyclists] = useState<Array<{ id: number, name: string, winPercentage: string, imageUrl: string }>>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleRaceChange = async (race: { id: string, name: string, index: number }) => {
    setSelectedRace(race)
    setIsOpen(false)
    setLoading(true)
    setError(null)

    try {
      const response = await axios.post('http://seito.lavbic.net:15000/predict', { index: race.index })
      const predictionData = response.data.prediction

      const cyclists = predictionData.map((cyclist: { rider_name: string, image_path: string, prediction: number }, i: number) => ({
        id: i + 1,
        name: cyclist.rider_name,
        winPercentage: (cyclist.prediction * 100).toFixed(2),
        imageUrl: `${cyclist.image_path}`
      }))

      setTopCyclists(cyclists)
    } catch (err) {
      setError('Failed to fetch predictions. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-cover bg-center p-4">
      <div className="max-w-4xl mx-auto bg-white/95 backdrop-blur-sm rounded-lg shadow-lg">
        <div className="p-6">
          <h2 className="text-2xl font-bold text-center mb-6">Cycling Race Predictor</h2>
          
          <div className="relative mb-6">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="w-full p-2 bg-white border border-gray-300 rounded-md shadow-sm text-left focus:outline-none focus:ring-2 focus:ring-primary"
              aria-haspopup="listbox"
              aria-expanded={isOpen}
            >
              <span className="block truncate">
                {selectedRace ? selectedRace.name : 'Select a race'}
              </span>
              <span className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
                <ChevronDown className="h-5 w-5 text-gray-400" aria-hidden="true" />
              </span>
            </button>
            {isOpen && (
              <select
                className="absolute z-10 mt-1 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm"
                size={races.length}
                onChange={(e) => handleRaceChange(races[e.target.selectedIndex])}
                value={selectedRace?.id}
              >
                {races.map((race) => (
                  <option
                    key={race.id}
                    value={race.id}
                    className={`cursor-default select-none relative py-2 pl-3 pr-9 hover:bg-primary hover:text-white ${
                      race.id === selectedRace?.id ? 'bg-primary text-white' : 'text-gray-900'
                    }`}
                  >
                    {race.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {loading && <p className="text-center">Loading predictions...</p>}
          {error && <p className="text-center text-red-500">{error}</p>}

          {selectedRace && topCyclists.length > 0 && !loading && (
            <div>
              <h3 className="text-lg font-semibold mb-2">Top 10 Cyclists</h3>
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="p-2 text-left">Rank</th>
                    <th className="p-2 text-left">Cyclist</th>
                    <th className="p-2 text-left">Win Likelihood</th>
                  </tr>
                </thead>
                <tbody>
                  {topCyclists.map((cyclist, index) => (
                    <tr key={cyclist.id} className="border-b">
                      <td className="p-2">{index + 1}</td>
                      <td className="p-2">
                        <div className="flex items-center space-x-2">
                          <Image
                            src={cyclist.imageUrl}
                            alt={`${cyclist.name}'s avatar`}
                            width={40}
                            height={40}
                            className="rounded-full"
                          />
                          <span>{cyclist.name}</span>
                        </div>
                      </td>
                      <td className="p-2">{cyclist.winPercentage}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
