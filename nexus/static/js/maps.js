/**
 * Google Maps Integration for NEXUS
 */

class MapsManager {
    constructor() {
        this.map = null;
        this.service = null;
        this.mapElement = document.getElementById('map-container');
        this.mapSection = document.getElementById('map-section');
    }

    async initMap(locationString) {
        if (!locationString || locationString.toLowerCase() === 'unknown' || locationString.toLowerCase() === 'unknown location') {
            this.mapSection.classList.add('hidden');
            return;
        }

        // Make section visible
        this.mapSection.classList.remove('hidden');

        // Ensure google maps is loaded by adding the script explicitly if it doesn't exist.
        // The prompt says we can fetch it via API key, but it's generated dynamically by backend usually.
        // We will attempt to use standard geolocation or just fallback gracefully placeholder.
        if (typeof google === 'undefined' || !google.maps) {
            this.mapElement.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: var(--color-muted);">
                    <span class="material-symbols-rounded" style="font-size: 2rem; margin-bottom: 0.5rem;">location_disabled</span>
                    <p>Map unavailable. Location detected: <strong>${locationString}</strong></p>
                </div>
            `;
            return;
        }

        try {
            // Geocode the string to lat/lng
            const geocoder = new google.maps.Geocoder();
            geocoder.geocode({ address: locationString }, (results, status) => {
                if (status === 'OK' && results[0]) {
                    const center = results[0].geometry.location;
                    
                    this.map = new google.maps.Map(this.mapElement, {
                        center: center,
                        zoom: 14,
                        mapTypeControl: false,
                        streetViewControl: false,
                        styles: [
                            { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
                            { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] },
                            { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] },
                            { featureType: "road", elementType: "geometry", stylers: [{ color: "#38414e" }] },
                            { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#212a37" }] },
                            { featureType: "water", elementType: "geometry", stylers: [{ color: "#17263c" }] }
                        ]
                    });

                    // Incident Marker
                    new google.maps.Marker({
                        map: this.map,
                        position: center,
                        title: "Incident Location",
                        icon: {
                            path: google.maps.SymbolPath.CIRCLE,
                            scale: 8,
                            fillColor: "#ff3b5e",
                            fillOpacity: 1,
                            strokeWeight: 2,
                            strokeColor: "#ffffff"
                        }
                    });

                    // Fetch nearby hospitals
                    this.service = new google.maps.places.PlacesService(this.map);
                    this.service.nearbySearch({
                        location: center,
                        radius: 5000,
                        type: ['hospital']
                    }, (placeResults, placeStatus) => {
                        if (placeStatus === google.maps.places.PlacesServiceStatus.OK && placeResults) {
                            placeResults.forEach((place) => {
                                new google.maps.Marker({
                                    map: this.map,
                                    position: place.geometry.location,
                                    title: place.name,
                                    icon: {
                                        path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
                                        scale: 5,
                                        fillColor: "#00d4aa",
                                        fillOpacity: 0.8,
                                        strokeWeight: 1,
                                        strokeColor: "#ffffff"
                                    }
                                });
                            });
                        }
                    });
                }
            });
        } catch (error) {
            console.error("Map initialization failed:", error);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.mapsManager = new MapsManager();
});
