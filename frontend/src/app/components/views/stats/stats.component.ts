import { AfterViewChecked, Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService, StatsPayload } from '../../../services/api.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-stats',
  templateUrl: './stats.component.html',
  styleUrls: ['./stats.component.scss']
})
export class StatsComponent implements OnInit, AfterViewChecked {

  @ViewChild('statsTable') private statsTable: ElementRef;
  @ViewChild('nameTable') private nameTable: ElementRef;
  data: StatsPayload;

  constructor(public api: ApiService, private route: ActivatedRoute) { }

  ngOnInit() {
    this.route.data.subscribe((routeData) => {
      if (!routeData.isCompanyWide) {
        this.api.getTeamStats().subscribe((data) => {
          this.data = data;
        });
      } else {
        this.api.getCompanyStats().subscribe((data) => {
          this.data = data;
        });
      }
      this.scrollToEnd();
    });
  }

  ngAfterViewChecked() {
    this.scrollToEnd();
    this.syncTableCellHeights();
  }

  syncTableCellHeights() {
    // because we use two separate tables to be able to have a responsive yet fixed
    // first column
    try {
      const cell = this.statsTable.nativeElement.querySelector('.stats-cell');
      this.nameTable.nativeElement.querySelectorAll('td').forEach(element => {
        element.height = `${cell.offsetHeight}px` ;
      });
    } catch (err) {}
  }

  scrollToEnd() {
    try {
      this.statsTable.nativeElement.scrollLeft = window.screen.width;
    } catch (err) {}
  }

}
