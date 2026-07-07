import { describe, expect, it } from 'vitest'

import {
  buildQmlHistoryCoilList,
  buildSearchResultsWithDetailFallback,
  selectVisibleCoilList,
  resolveCoilSearch,
  shouldUseCoilDetailFallback,
} from './coilSearch'

describe('coil search resolver', () => {
  it('treats empty input as realtime list mode', () => {
    expect(resolveCoilSearch('   ')).toEqual({ kind: 'none', text: '' })
  })

  it('routes pure numeric input to backend coil id search', () => {
    expect(resolveCoilSearch(' 16019 ')).toEqual({
      kind: 'id',
      text: '16019',
      coilId: 16019,
    })
  })

  it('routes numeric text as a coil number when the QML coil-number search page is selected', () => {
    expect(resolveCoilSearch(' 202607030001 ', 'coilNo')).toEqual({
      kind: 'coilNo',
      text: '202607030001',
    })
  })

  it('routes serial-number text to backend coil id search only from the QML serial-number page', () => {
    expect(resolveCoilSearch(' 16019 ', 'coilId')).toEqual({
      kind: 'id',
      text: '16019',
      coilId: 16019,
    })
    expect(resolveCoilSearch('4V07441200', 'coilId')).toEqual({ kind: 'none', text: '' })
  })

  it('routes mixed or textual input to backend coil number search', () => {
    expect(resolveCoilSearch('4V07441200')).toEqual({
      kind: 'coilNo',
      text: '4V07441200',
    })
  })

  it('stores search results in QML history-list order', () => {
    const backendRows = [{ id: 1 }, { id: 2 }, { id: 3 }]

    expect(buildQmlHistoryCoilList(backendRows)).toEqual([{ id: 3 }, { id: 2 }, { id: 1 }])
    expect(backendRows).toEqual([{ id: 1 }, { id: 2 }, { id: 3 }])
  })

  it('selects realtime or history rows without losing either list', () => {
    const realtimeRows = [{ id: 193113 }]
    const historyRows = [{ id: 16019 }]

    expect(selectVisibleCoilList('realtime', realtimeRows, historyRows)).toBe(realtimeRows)
    expect(selectVisibleCoilList('history', realtimeRows, historyRows)).toBe(historyRows)
  })

  it('uses detail fallback when numeric backend search has no summary rows', () => {
    const request = resolveCoilSearch('14852')

    expect(shouldUseCoilDetailFallback(request, [])).toBe(true)
    expect(
      buildSearchResultsWithDetailFallback(request, [], {
        id: 14852,
        coilNo: '4V07124400',
      }),
    ).toEqual([{ id: 14852, coilNo: '4V07124400' }])
  })

  it('does not use detail fallback when search rows already exist or the detail id differs', () => {
    const request = resolveCoilSearch('14852')
    const backendRows = [{ id: 14852, coilNo: 'summary-row' }]

    expect(shouldUseCoilDetailFallback(request, backendRows)).toBe(false)
    expect(buildSearchResultsWithDetailFallback(request, backendRows, { id: 14852, coilNo: 'detail-row' })).toBe(
      backendRows,
    )
    expect(buildSearchResultsWithDetailFallback(request, [], { id: 99 })).toEqual([])
    expect(buildSearchResultsWithDetailFallback(resolveCoilSearch('4V07124400'), [], { id: 14852 })).toEqual([])
  })
})
