import {Component, OnInit, Input, Directive, Output, EventEmitter, ViewChildren, QueryList} from '@angular/core';
import {EnrolleeItem, EnrolleesPayload} from "../../../services/api.service";

// ripped from https://ng-bootstrap.github.io/#/components/table/examples#sortable
export type SortColumn = keyof EnrolleeItem | '';
export type SortDirection = 'asc' | 'desc' | '';
const rotate: { [key: string]: SortDirection } = {'asc': 'desc', 'desc': '', '': 'asc'};
const compare = (v1: string, v2: string) => v1 < v2 ? -1 : v1 > v2 ? 1 : 0;

export interface SortEvent {
  column: SortColumn;
  direction: SortDirection;
}

@Directive({
  selector: 'th[sortable]',
  host: {
    '[class.asc]': 'direction === "asc"',
    '[class.desc]': 'direction === "desc"',
    '(click)': 'rotate()'
  }
})
export class NgbdSortableHeader {

  @Input() sortable: SortColumn = '';
  @Input() direction: SortDirection = '';
  @Output() sort = new EventEmitter<SortEvent>();

  rotate() {
    this.direction = rotate[this.direction];
    this.sort.emit({column: this.sortable, direction: this.direction});
  }
}

@Component({
  selector: 'app-feedback-user-list',
  templateUrl: './feedback-user-list.component.html',
  styleUrls: ['./feedback-user-list.component.scss']
})
export class FeedbackUserListComponent implements OnInit {

  @Input() title: string;
  @Input() description: string;
  @Input() users: EnrolleeItem[];
  @ViewChildren(NgbdSortableHeader) headers: QueryList<NgbdSortableHeader>;

  constructor() { }

  ngOnInit(): void {
  }
  onSort({column, direction}: SortEvent) {

    // resetting other headers
    this.headers.forEach(header => {
      if (header.sortable !== column) {
        header.direction = '';
      }
    });

    // sorting countries
    if (direction === '' || column === '') {
      this.users = this.users;
    } else {
      this.users = [...this.users].sort((a, b) => {
        const res = compare(`${a[column]}`, `${b[column]}`);
        return direction === 'asc' ? res : -res;
      });
    }
  }
}
