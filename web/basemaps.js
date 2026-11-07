/* basemaps.js — the map backgrounds used by every map on the site (main page, station pages, trip check).
   UNEBASE(mode, dark, metric) returns a Leaflet layer for:
     'street'    Esri's ocean map (depth shading) while zoomed out; past zoom 13, where that map has no detail
                 along this coast ("Map data not yet available"), it switches by itself to Esri's street map.
                 Dark theme: Esri's dark grey map, enlarged past its last detailed level instead of erroring.
     'satellite' Esri World Imagery with place and road names on top, sharp down to docks and buildings.
     'chart'     NOAA's nautical chart (soundings and depth contours, in feet or metres).
   Also accepts the older names 'map' (= street). */
(function () {
  const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/';
  const tile = (path, o) => L.tileLayer(ESRI + path + '/MapServer/tile/{z}/{y}/{x}', Object.assign({ maxZoom: 19 }, o));
  const OCEAN_TOP = 13;     // last zoom level the ocean map has detail for here
  window.UNEBASE = function (mode, dark, metric) {
    if (mode === 'chart')
      return L.tileLayer.wms('https://gis.charttools.noaa.gov/arcgis/rest/services/MCS/NOAAChartDisplay/MapServer/exts/MaritimeChartService/WMSServer', {
        layers: '0,1,2,3,4,5,6,7', format: 'image/png', transparent: false, version: '1.3.0', maxZoom: 19,
        display_params: JSON.stringify({ ECDISParameters: { DynamicParameters: { Parameter: [{ name: 'DisplayDepthUnits', value: metric ? 1 : 2 }] } } }),
        attribution: 'NOAA Office of Coast Survey — not for navigation' });
    if (mode === 'satellite')
      return L.layerGroup([
        tile('World_Imagery', { maxNativeZoom: 19, attribution: 'Imagery: Esri, Maxar, Earthstar Geographics, USDA, USGS' }),
        tile('Reference/World_Transportation', { maxNativeZoom: 19, opacity: .7 }),
        tile('Reference/World_Boundaries_and_Places', { maxNativeZoom: 19 })]);
    if (dark)
      return L.layerGroup([
        tile('Canvas/World_Dark_Gray_Base', { maxNativeZoom: 16, attribution: 'Esri, HERE, Garmin, &copy; OpenStreetMap contributors' }),
        tile('Canvas/World_Dark_Gray_Reference', { maxNativeZoom: 16 })]);
    return L.layerGroup([
      tile('Ocean/World_Ocean_Base', { maxZoom: OCEAN_TOP, attribution: 'Esri, GEBCO, NOAA, Garmin, HERE, &copy; OpenStreetMap contributors' }),
      tile('Ocean/World_Ocean_Reference', { maxZoom: OCEAN_TOP }),
      tile('World_Street_Map', { minZoom: OCEAN_TOP + 1, maxNativeZoom: 19, attribution: 'Esri, HERE, Garmin, USGS, &copy; OpenStreetMap contributors' })]);
  };
})();
