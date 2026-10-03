// Every animation, both rounds. The renderer and stage look ids up here.
import { ANIMS } from './anims.js';
import { ANIMS_V2 } from './anims-v2.js';

export const ALL = [...ANIMS, ...ANIMS_V2];
export const byId = id => ALL.find(a => a.id === id);
