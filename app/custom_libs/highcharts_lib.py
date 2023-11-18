# --------------- Highcharts functions ------------------------#

def to_highchart(graphtype, series, series_drilldown, title, subtitle, value_label='k€'):
    # title shall be a string
    # graphtype shall be a string indicating the chart type (pie, line, chart, etc
    # series shall be a list
    chart = {'plotShadow': 'false', 'type': graphtype}
    title = {'text': title}
    subtitle = {'text': subtitle}
    series = series
    tooltip = {'pointFormat': '{series.name}: <b>{point.percentage:.1f}%</b>'}
    plotOptions = {graphtype: {'allowPointSelect': 'true', 'cursor': 'pointer', 'dataLabels': {'enabled': 'true',
                                                                                               'format': '<b>{point.name}</b>: {point.y:.1f} ' + value_label}}}
    drilldown = {'series': series_drilldown}
    return '{' + f'chart: {chart}, tooltip: {tooltip}, title: {title}, subtitle: {subtitle}, plotOptions: {plotOptions}, series: {series}, drilldown: {drilldown}' + '}'


def to_gantt_highchart(series, title, extras=False):
    title = {'text': title}
    series = series
    xAxis = '{minPadding: 0.05, maxPadding: 0.05}'
    flag = 'false'
    if extras:
        flag = 'true'
    navigator = "{enabled: " + flag + ", liveRedraw: true,series: {type: 'gantt', pointPlacement: 0.5,pointPadding: 0.25}, yAxis: {min: 0,max: 3, reversed: true, categories: []}}"
    scrollbar = "{enabled: " + flag + "}"
    rangeSelector = "{enabled: " + flag + ",selected: 0}"
    return '{' + f'title: {title}, series: {series}, xAxis : {xAxis}, navigator: {navigator}, scrollbar: {scrollbar}, rangeSelector: {rangeSelector}' + '}'


def to_map_highchart(series, title):
    title = {'text': title}
    chart = {'map': 'custom/europe'}
    legend = '{enabled: false}'
    series = series

    return '{' + f'chart: {chart}, title: {title}, legend: {legend}, series: {series}' + '}'
