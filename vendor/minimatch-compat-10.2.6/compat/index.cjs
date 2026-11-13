'use strict'
const engine = require('../dist/commonjs/index.js')
module.exports = Object.assign(engine.minimatch, engine)
