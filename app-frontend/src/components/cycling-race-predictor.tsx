"use client"

import React, { useState } from 'react'
import Image from 'next/image'
import { ChevronDown } from 'lucide-react'

const races = [
  { id: 'tour-de-france', name: 'Tour de France' },
  { id: 'giro-italia', name: 'Giro d\'Italia' },
  { id: 'vuelta-espana', name: 'Vuelta a España' },
  { id: 'paris-roubaix', name: 'Paris-Roubaix' },
]

const generateTopCyclists = () => {
  return Array.from({ length: 10 }, (_, i) => ({
    id: i + 1,
    name: `Cyclist ${i + 1}`,
    winPercentage: (Math.random() * 100).toFixed(2),
    imageUrl: `/placeholder.svg?height=40&width=40&text=${i + 1}`
  })).sort((a, b) => Number(b.winPercentage) - Number(a.winPercentage))
}

export default function CyclingRacePredictor() {
  const [selectedRace, setSelectedRace] = useState<string | undefined>()
  const [topCyclists, setTopCyclists] = useState<Array<{ id: number, name: string, winPercentage: string, imageUrl: string }>>([])
  const [isOpen, setIsOpen] = useState(false)

  const handleRaceChange = (value: string) => {
    setSelectedRace(value)
    setTopCyclists(generateTopCyclists())
    setIsOpen(false)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary to-secondary p-4">
      <div className="max-w-4xl mx-auto bg-white/90 backdrop-blur-sm rounded-lg shadow-lg">
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
                {selectedRace ? races.find(race => race.id === selectedRace)?.name : 'Select a race'}
              </span>
              <span className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
                <ChevronDown className="h-5 w-5 text-gray-400" aria-hidden="true" />
              </span>
            </button>
            {isOpen && (
              <select
                className="absolute z-10 mt-1 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm"
                size={races.length}
                value={selectedRace}
                onChange={(e) => handleRaceChange(e.target.value)}
              >
                {races.map((race) => (
                  <option
                    key={race.id}
                    value={race.id}
                    className={`cursor-default select-none relative py-2 pl-3 pr-9 hover:bg-primary hover:text-white ${
                      race.id === selectedRace ? 'bg-primary text-white' : 'text-gray-900'
                    }`}
                  >
                    {race.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {selectedRace && topCyclists.length > 0 && (
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
