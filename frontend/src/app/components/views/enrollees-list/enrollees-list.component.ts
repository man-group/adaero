import {Component, Directive, EventEmitter, Input, OnInit, Output, QueryList, ViewChildren} from '@angular/core';
import {ApiService, EnrolleeItem, EnrolleesPayload, MessageTemplatePayload} from '../../../services/api.service';
import {Observable} from 'rxjs';




@Component({
  selector: 'app-enrollees-list',
  templateUrl: './enrollees-list.component.html',
  styleUrls: ['./enrollees-list.component.scss']
})
export class EnrolleesListComponent implements OnInit {

  constructor(public api: ApiService) {
  }

  data: EnrolleesPayload;
  message: MessageTemplatePayload;

  ngOnInit() {
    this.api.getNominees().subscribe(data => {
      this.data = data
    });

  }



}
