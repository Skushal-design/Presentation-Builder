window.PROJECT_TITLE = "V-Ray Render Pass Breakdown";
window.SETTINGS = {"logo": "", "edge_show": true, "edge_color": "#ffffff", "edge_width": 2.0, "edge_glow": true, "show_topbar": true, "show_brand": true, "show_counter": true, "show_pass_name": true, "show_tags": true, "show_timeline": true, "show_hint": true, "show_caption": true};
window.PASSES = [
  {
    "name": "Final RGB / Beauty",
    "image": "assets/passes/Room.RGB_color.jpg",
    "description": "",
    "slide_ms": 1000,
    "pause_ms": 600,
    "hold": 10.0,
    "final": false,
    "blend": "normal",
    "transition": "wipe_angle",
    "wipe_angle": 45.0,
    "hidden": false,
    "opacity": 100.0
  },
  {
    "name": "Room Vrayao",
    "image": "assets/passes/Room.VRayAO.jpg",
    "description": "",
    "slide_ms": 1000,
    "pause_ms": 600,
    "hold": 10.0,
    "final": false,
    "blend": "multiply",
    "transition": "wipe_angle",
    "wipe_angle": 45.0,
    "hidden": false,
    "opacity": 100.0
  },
  {
    "name": "Refraction",
    "image": "assets/passes/Room.VRayRefraction.jpg",
    "description": "",
    "slide_ms": 1000,
    "pause_ms": 600,
    "hold": 10.0,
    "final": false,
    "blend": "add",
    "transition": "wipe_angle",
    "wipe_angle": 45.0,
    "hidden": false,
    "opacity": 100.0
  }
];
