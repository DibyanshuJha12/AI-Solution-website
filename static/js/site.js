import { onReady } from "./modules/dom.js";
import { initSite } from "./modules/site-core.js";
import "./chatbot.js";


onReady(() => {
  initSite();
});
