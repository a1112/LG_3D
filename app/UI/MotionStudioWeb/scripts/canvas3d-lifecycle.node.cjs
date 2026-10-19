const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const path = require('node:path')
const test = require('node:test')
const vm = require('node:vm')
const { transformSync } = require('esbuild')
const THREE = require('three')

// Explicit Node suite, outside Vitest's default *.test.* discovery.
// Controlled hooks/host objects, not ReactDOM, R3F, WebGL, or native acceptance.
// Only the private export is added for test routing; application logic is unchanged.
const sourcePath = path.join(__dirname, '../src/components/Canvas3D/index.tsx')
const parserPath = path.join(__dirname, '../src/utils/dataParser.ts')
const controlsPath = path.join(__dirname, '../src/components/Canvas3D/utils.ts')

function evaluate(source, filename, context, imports) {
  const module = { exports: {} }
  const code = transformSync(source, {
    loader: filename.endsWith('.tsx') ? 'tsx' : 'ts', format: 'cjs', target: 'es2020',
    jsx: 'transform', jsxFactory: '__jsx', jsxFragment: '__Fragment',
  }).code
  vm.runInNewContext(code, {
    ...context, module, exports: module.exports,
    require(name) {
      if (!Object.hasOwn(imports, name)) throw new Error(`unapproved import in synthetic fixture: ${name}`)
      return imports[name]
    },
  }, { filename })
  return module.exports
}

function fixture() {
  let current = null
  const geometries = []
  const materials = []
  const parseInputs = []
  const frames = new Map()
  const allFrames = new Map()
  const cancelledFrames = []
  const urls = new Map()
  const revokedUrls = []
  let nextFrame = 0
  let nextUrl = 0
  class OwnedMaterial extends THREE.PointsMaterial {
    constructor(options) {
      super(options)
      this.disposals = 0
      this.addEventListener('dispose', () => { this.disposals += 1 })
      materials.push(this)
    }
  }
  const context = {
    ArrayBuffer, Uint8Array, Float32Array, DataView, Blob,
    console: { error() {}, warn() {}, log() {} },
    __Fragment: 'synthetic-fragment',
    __jsx: (type, props, ...children) => ({ type, props: {
      ...props, children: children.length === 1 ? children[0] : children,
    } }),
    URL: {
      createObjectURL(blob) { const url = `blob:synthetic-${++nextUrl}`; urls.set(url, blob); return url },
      revokeObjectURL(url) { revokedUrls.push(url); urls.delete(url) },
    },
    requestAnimationFrame(callback) {
      const id = ++nextFrame
      frames.set(id, callback)
      allFrames.set(id, callback)
      return id
    },
    cancelAnimationFrame(id) { cancelledFrames.push(id); frames.delete(id) },
  }
  const parser = evaluate(readFileSync(parserPath, 'utf8'), parserPath, context, { three: THREE })
  const controls = evaluate(readFileSync(controlsPath, 'utf8'), controlsPath, context, {})
  const utils = {
    ...parser,
    createPointCloudGeometry(...args) {
      const geometry = parser.createPointCloudGeometry(...args)
      geometry.disposals = 0
      geometry.addEventListener('dispose', () => { geometry.disposals += 1 })
      geometries.push(geometry)
      return geometry
    },
    parseHeightData(data) { parseInputs.push(data); return parser.parseHeightData(data) },
  }
  const component = evaluate(readFileSync(sourcePath, 'utf8') + '\nexport { PointCloud };\n', sourcePath, context, {
    react: {
      useRef: (value) => current.useRef(value),
      useState: (value) => current.useState(value),
      useMemo: (factory, deps) => current.useMemo(factory, deps),
      useEffect: (setup, deps) => current.useEffect(setup, deps),
    },
    '@react-three/fiber': { Canvas: 'synthetic-canvas', useFrame() {} },
    '@react-three/drei': {
      OrbitControls: 'synthetic-orbit', Grid: 'synthetic-grid', PerspectiveCamera: 'synthetic-camera',
    },
    three: { ...THREE, PointsMaterial: OwnedMaterial },
    '@/utils': utils,
    './utils': controls,
    './Canvas3D.css': {},
  })

  class Hooks {
    constructor(render) {
      this.component = render
      this.slots = []
      this.cursor = 0
      this.effects = []
      this.hosts = new Map()
      this.mounted = true
      this.lateWrites = 0
    }
    slot(kind, initialize) {
      const index = this.cursor++
      if (!this.slots[index]) this.slots[index] = { kind, ...initialize() }
      assert.equal(this.slots[index].kind, kind, 'hook order must remain stable')
      return this.slots[index]
    }
    useRef(initial) { return this.slot('ref', () => ({ current: initial })) }
    useState(initial) {
      const state = this.slot('state', () => ({ value: initial }))
      return [state.value, (action) => {
        if (!this.mounted) { this.lateWrites += 1; return }
        const next = typeof action === 'function' ? action(state.value) : action
        if (!Object.is(next, state.value)) { state.value = next; this.dirty = true }
      }]
    }
    changed(previous, next) {
      return !previous || previous.length !== next.length || next.some((value, index) => !Object.is(value, previous[index]))
    }
    useMemo(factory, deps) {
      const state = this.slot('memo', () => ({}))
      if (this.changed(state.deps, deps)) { state.value = factory(); state.deps = deps }
      return state.value
    }
    useEffect(setup, deps) {
      const state = this.slot('effect', () => ({}))
      if (this.changed(state.deps, deps)) {
        state.deps = deps
        state.setup = setup
        this.effects.push(state)
      }
    }
    attach(node, parent = null, key = 'root') {
      if (!node || typeof node !== 'object') return
      if (Array.isArray(node)) { node.forEach((child, index) => this.attach(child, parent, `${key}.${index}`)); return }
      let host = parent
      if (node.type === 'group' || node.type === 'points') {
        if (!this.hosts.has(key)) this.hosts.set(key, node.type === 'group' ? new THREE.Group() : new THREE.Points())
        host = this.hosts.get(key)
        if (parent && host.parent !== parent) parent.add(host)
        if (node.props.ref) node.props.ref.current = host
        if (node.props.scale) host.scale.set(...node.props.scale)
      }
      this.attach(node.props?.children, host, `${key}.children`)
    }
    render(props) {
      this.props = props
      for (let pass = 0; pass < 20; pass += 1) {
        this.dirty = false
        this.cursor = 0
        this.effects = []
        current = this
        try { this.tree = this.component(props) } finally { current = null }
        this.attach(this.tree)
        for (const state of this.effects) {
          state.cleanup?.()
          state.cleanup = state.setup()
        }
        if (!this.dirty) return this.tree
      }
      throw new Error('synthetic hook render did not settle')
    }
    replayEffects() {
      for (const state of this.slots.filter((entry) => entry.kind === 'effect')) {
        state.cleanup?.()
        state.cleanup = state.setup()
      }
      return this.render(this.props)
    }
    unmount() {
      this.mounted = false
      for (const state of this.slots.filter((entry) => entry.kind === 'effect')) state.cleanup?.()
    }
    find(type) {
      function visit(node) {
        if (!node || typeof node !== 'object') return null
        if (Array.isArray(node)) return node.map(visit).find(Boolean) ?? null
        if (node.type === type || node.type?.name === type) return node
        return visit(node.props?.children)
      }
      return visit(this.tree)
    }
  }
  const cloud = () => new Hooks(component.PointCloud)
  const canvas = () => new Hooks(component.default)
  const deliverFrame = (id) => { frames.delete(id); allFrames.get(id)?.(0) }
  const retained = (resources) => resources.filter((resource) => resource.disposals === 0).length
  return { cloud, canvas, geometries, materials, parseInputs, frames, allFrames, cancelledFrames,
    urls, revokedUrls, deliverFrame, retained }
}

function cloudData(value = 1) {
  return { count: 1, positions: new Float32Array([value, 2, 3]), colors: new Float32Array([1, 0, 0]) }
}
function heightBuffer(value = 1) {
  const buffer = new ArrayBuffer(16)
  const view = new DataView(buffer)
  view.setFloat32(0, value, true); view.setFloat32(4, 2, true); view.setFloat32(8, 3, true)
  return buffer
}
function pngBuffer() { return new Uint8Array([0x89, 0x50, 0x4e, 0x47]).buffer }

test('forty point-cloud replacements release every owned geometry and material', (t) => {
  const f = fixture(); const runtime = f.cloud()
  for (let i = 0; i < 40; i += 1) runtime.render({ parsedData: cloudData(i), zScale: 0.5 })
  const beforeUnmount = { geometry: f.retained(f.geometries), material: f.retained(f.materials) }
  runtime.unmount()
  const afterUnmount = { geometry: f.retained(f.geometries), material: f.retained(f.materials) }
  t.diagnostic(JSON.stringify({ replacements: 40, beforeUnmount, afterUnmount }))
  assert.deepEqual(beforeUnmount, { geometry: 1, material: 1 })
  assert.deepEqual(afterUnmount, { geometry: 0, material: 0 })
  assert.ok([...f.geometries, ...f.materials].every((resource) => resource.disposals === 1))
})

test('a point-cloud unmount releases its last pair and detaches the owned points', () => {
  const f = fixture(); const runtime = f.cloud()
  runtime.render({ parsedData: cloudData(), zScale: 0.5 })
  runtime.unmount()
  assert.equal(f.retained(f.geometries), 0)
  assert.equal(f.retained(f.materials), 0)
  assert.equal(runtime.hosts.get('root').children.length, 0)
})

test('effect cleanup and replay release each point-cloud pair once', () => {
  const f = fixture(); const runtime = f.cloud()
  runtime.render({ parsedData: cloudData(), zScale: 0.5 })
  runtime.replayEffects()
  runtime.unmount()
  assert.equal(f.geometries.length, 2)
  assert.equal(f.materials.length, 2)
  assert.ok([...f.geometries, ...f.materials].every((resource) => resource.disposals === 1))
})

test('changing only z-scale preserves point-cloud buffers and material', () => {
  const f = fixture(); const runtime = f.cloud(); const data = cloudData()
  runtime.render({ parsedData: data, zScale: 0.5 })
  runtime.render({ parsedData: data, zScale: 1.5 })
  assert.equal(f.geometries.length, 1)
  assert.equal(f.materials.length, 1)
  assert.equal(runtime.hosts.get('root').scale.z, 1.5)
  runtime.unmount()
})

test('forty superseded binary inputs retain only the latest scheduled parse', (t) => {
  const f = fixture(); const runtime = f.canvas()
  for (let i = 0; i < 40; i += 1) runtime.render({ data: heightBuffer(i) })
  const beforeUnmount = f.frames.size
  runtime.unmount()
  t.diagnostic(JSON.stringify({ replacements: 40, beforeUnmount, afterUnmount: f.frames.size }))
  assert.equal(beforeUnmount, 1)
  assert.equal(f.frames.size, 0)
})

test('a retired binary callback cannot replace the current height-line fallback', () => {
  const f = fixture(); const runtime = f.canvas()
  runtime.render({ data: heightBuffer(99) })
  const oldFrame = [...f.frames.keys()][0]
  const props = { data: null, heightLineSegments: [{ points: [[0, 0, 1], [1, 0, 2]] }] }
  runtime.render(props)
  f.deliverFrame(oldFrame)
  runtime.render(props)
  assert.equal(f.parseInputs.length, 0)
  assert.equal(runtime.find('Scene').props.parsedData.count, 2)
})

test('a queued callback delivered after unmount performs no parse or state write', () => {
  const f = fixture(); const runtime = f.canvas()
  runtime.render({ data: heightBuffer() })
  const oldFrame = [...f.frames.keys()][0]
  runtime.unmount()
  f.deliverFrame(oldFrame)
  assert.equal(f.frames.size, 0)
  assert.equal(f.parseInputs.length, 0)
  assert.equal(runtime.lateWrites, 0)
})

test('the current binary input still parses and displays the expected point', () => {
  const f = fixture(); const runtime = f.canvas(); const data = heightBuffer(7)
  runtime.render({ data })
  f.deliverFrame([...f.frames.keys()][0])
  runtime.render({ data })
  assert.equal(f.parseInputs.length, 1)
  assert.deepEqual(Array.from(runtime.find('Scene').props.parsedData.positions), [7, 2, 3])
  assert.equal(runtime.find('Scene').props.isLoading, false)
  runtime.unmount()
})

test('switching binary input to a raster retires the parse and preserves the live URL', () => {
  const f = fixture(); const runtime = f.canvas()
  runtime.render({ data: heightBuffer() })
  const oldFrame = [...f.frames.keys()][0]
  const props = { data: pngBuffer() }
  runtime.render(props)
  f.deliverFrame(oldFrame)
  runtime.render(props)
  assert.equal(f.parseInputs.length, 0)
  assert.equal(f.frames.size, 0)
  assert.equal(f.urls.size, 1)
  assert.ok(f.urls.has(runtime.find('img').props.src))
  runtime.unmount()
  assert.equal(f.urls.size, 0)
})

test('each raster URL is revoked once across forty replacements and unmount', () => {
  const f = fixture(); const runtime = f.canvas()
  for (let i = 0; i < 40; i += 1) runtime.render({ data: pngBuffer() })
  assert.equal(f.urls.size, 1)
  runtime.unmount()
  assert.equal(f.urls.size, 0)
  assert.equal(f.revokedUrls.length, 40)
  assert.equal(new Set(f.revokedUrls).size, 40)
})

test('raster effect cleanup and replay preserve only the current owner', () => {
  const f = fixture(); const runtime = f.canvas()
  runtime.render({ data: pngBuffer() })
  runtime.replayEffects()
  assert.equal(f.urls.size, 1)
  assert.ok(f.urls.has(runtime.find('img').props.src))
  runtime.unmount()
  assert.equal(f.urls.size, 0)
  assert.equal(f.revokedUrls.length, 2)
})

test('rerendering the same raster input keeps its URL until unmount', () => {
  const f = fixture(); const runtime = f.canvas(); const props = { data: pngBuffer() }
  runtime.render(props)
  const url = runtime.find('img').props.src
  runtime.render(props)
  assert.equal(runtime.find('img').props.src, url)
  assert.equal(f.revokedUrls.length, 0)
  runtime.unmount()
  assert.deepEqual(f.revokedUrls, [url])
})
