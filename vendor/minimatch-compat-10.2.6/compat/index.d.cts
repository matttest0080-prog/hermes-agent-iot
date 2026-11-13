import * as engine from '../dist/commonjs/index.js'
declare function minimatch(path: string, pattern: string, options?: engine.MinimatchOptions): boolean
declare namespace minimatch {
  const minimatch: typeof engine.minimatch
  const Minimatch: typeof engine.Minimatch
  type Minimatch = engine.Minimatch
  type IMinimatch = engine.Minimatch
  type IOptions = engine.MinimatchOptions
  type MinimatchOptions = engine.MinimatchOptions
  type MMRegExp = engine.MMRegExp
  type ParseReturn = engine.ParseReturn
  type ParseReturnFiltered = engine.ParseReturnFiltered
  type Platform = engine.Platform
  type Sep = engine.Sep
  const GLOBSTAR: typeof engine.GLOBSTAR
  const sep: typeof engine.sep
  const filter: typeof engine.filter
  const defaults: typeof engine.defaults
  const braceExpand: typeof engine.braceExpand
  const makeRe: typeof engine.makeRe
  const match: typeof engine.match
  const AST: typeof engine.AST
  const escape: typeof engine.escape
  const unescape: typeof engine.unescape
}
export = minimatch
