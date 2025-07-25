/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { isEmpty, isEqual, noop } from 'lodash';
import {
  BinaryAdhocFilter,
  css,
  ensureIsArray,
  fetchTimeRange,
  getTimeOffset,
  parseDttmToDate,
  SimpleAdhocFilter,
  t,
} from '@superset-ui/core';
import ControlHeader, {
  ControlHeaderProps,
} from 'src/explore/components/ControlHeader';
import { RootState } from 'src/views/store';
import { DEFAULT_DATE_PATTERN } from '@superset-ui/chart-controls';
import { extendedDayjs } from '@superset-ui/core/utils/dates';

const DAYJS_FORMAT = 'YYYY-MM-DD';

const isTimeRangeEqual = (
  left: BinaryAdhocFilter[],
  right: BinaryAdhocFilter[],
) => isEqual(left, right);

const isShiftEqual = (left: string[], right: string[]) => isEqual(left, right);

type ComparisonRangeLabelProps = ControlHeaderProps & {
  multi?: boolean;
};

const oldChoices = {
  r: 'inherit',
  y: '1 year ago',
  m: '1 month ago',
  w: '1 week ago',
  c: 'custom',
};

export const ComparisonRangeLabel = ({
  multi = true,
}: ComparisonRangeLabelProps) => {
  noop(multi); // This is to avoid unused variable warning, can be removed if not needed

  const [labels, setLabels] = useState<string[]>([]);
  const currentTimeRangeFilters = useSelector<RootState, BinaryAdhocFilter[]>(
    state =>
      state.explore.form_data.adhoc_filters.filter(
        (adhoc_filter: SimpleAdhocFilter) =>
          adhoc_filter.operator === 'TEMPORAL_RANGE',
      ),
    isTimeRangeEqual,
  );
  const previousCustomFilter = useSelector<RootState, BinaryAdhocFilter[]>(
    state =>
      state.explore.form_data.adhoc_custom?.filter(
        (adhoc_filter: SimpleAdhocFilter) =>
          adhoc_filter.operator === 'TEMPORAL_RANGE',
      ),
    isTimeRangeEqual,
  );
  const shifts = useSelector<RootState, string[]>(state => {
    const formData = state.explore.form_data || {};
    if (!formData?.time_compare) {
      const previousTimeComparison = formData.time_comparison || '';
      if (oldChoices.hasOwnProperty(previousTimeComparison)) {
        const previousChoice =
          oldChoices[previousTimeComparison as keyof typeof oldChoices];
        return [previousChoice];
      }
    }
    return formData?.time_compare;
  }, isShiftEqual);
  const startDate = useSelector<RootState, string>(
    state => state.explore.form_data.start_date_offset,
  );

  useEffect(() => {
    const shiftsArray = ensureIsArray(shifts);
    if (
      isEmpty(currentTimeRangeFilters) ||
      (isEmpty(shiftsArray) && !startDate)
    ) {
      setLabels([]);
    } else if (!isEmpty(shifts) || startDate) {
      let useStartDate = startDate;
      if (!startDate && !isEmpty(previousCustomFilter)) {
        useStartDate = previousCustomFilter[0]?.comparator.split(' : ')[0];
        useStartDate = extendedDayjs(parseDttmToDate(useStartDate)).format(
          DAYJS_FORMAT,
        );
      }
      const promises = currentTimeRangeFilters.map(filter => {
        const nonCustomNorInheritShifts =
          shiftsArray.filter(
            (shift: string) => shift !== 'custom' && shift !== 'inherit',
          ) || [];
        const customOrInheritShifts =
          shiftsArray.filter(
            (shift: string) => shift === 'custom' || shift === 'inherit',
          ) || [];

        // There's no custom or inherit to compute, so we can just fetch the time range
        if (isEmpty(customOrInheritShifts)) {
          return fetchTimeRange(
            filter.comparator,
            filter.subject,
            ensureIsArray(nonCustomNorInheritShifts),
          );
        }
        // Need to compute custom or inherit shifts first and then mix with the non custom or inherit shifts
        if (
          (ensureIsArray(customOrInheritShifts).includes('custom') &&
            startDate) ||
          ensureIsArray(customOrInheritShifts).includes('inherit')
        ) {
          return fetchTimeRange(filter.comparator, filter.subject).then(res => {
            const dates = res?.value?.match(DEFAULT_DATE_PATTERN);
            const [parsedStartDate, parsedEndDate] = dates ?? [];
            if (parsedStartDate) {
              const parsedDateDayjs = extendedDayjs(
                parseDttmToDate(parsedStartDate),
              );
              const startDateDayjs = extendedDayjs(parseDttmToDate(startDate));
              if (
                startDateDayjs.isSameOrBefore(parsedDateDayjs) ||
                !startDate
              ) {
                const postProcessedShifts = getTimeOffset({
                  timeRangeFilter: {
                    ...filter,
                    comparator: `${parsedStartDate} : ${parsedEndDate}`,
                  },
                  shifts: customOrInheritShifts,
                  startDate: useStartDate,
                  includeFutureOffsets: false, // So we don't trigger requests for future dates
                });
                return fetchTimeRange(
                  filter.comparator,
                  filter.subject,
                  ensureIsArray(
                    postProcessedShifts.concat(nonCustomNorInheritShifts),
                  ),
                );
              }
            }
            return Promise.resolve({ value: '' });
          });
        }
        return Promise.resolve({ value: '' });
      });
      Promise.all(promises).then(res => {
        // access the value property inside the res and set the labels with it in the state
        setLabels(res.map(r => r.value ?? ''));
      });
    }
  }, [currentTimeRangeFilters, shifts, startDate]);

  return labels.length ? (
    <>
      <ControlHeader label={t('Actual range for comparison')} />
      {labels.flat().map(label => (
        <>
          <div
            css={theme => css`
              font-size: ${theme.fontSize}px;
              color: ${theme.colorText};
            `}
            key={label}
          >
            {label}
          </div>
        </>
      ))}
    </>
  ) : null;
};
