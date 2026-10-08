// Every animation, all rounds. The renderer and stage look ids up here.
import { ANIMS } from './anims.js';
import { ANIMS_V2 } from './anims-v2.js';
import { ANIMS_V3 } from './anims-v3.js';

export const ALL = [...ANIMS, ...ANIMS_V2, ...ANIMS_V3];
export const byId = id => ALL.find(a => a.id === id);
